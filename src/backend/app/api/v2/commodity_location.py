import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import (
    ColumnElement,
    Select,
    and_,
    distinct,
    func,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import array_agg  # type: ignore
from sqlalchemy.orm import aliased
from sqlalchemy.sql.selectable import Subquery
from src.backend.app.access import SafeSession
from src.backend.app.config import settings
from src.backend.app.models.admin_region import AdminRegion
from src.backend.app.models.commodity_location_entity import (
    CommodityLocationEntity,
)
from src.backend.app.models.export.exported_commodity_location import (
    ExportedCommodityLocation,
)
from src.backend.app.schemas.api_v2.commodity_location import (
    CommodityLocationSortKey,
)
from src.backend.app.schemas.commodity_source import (
    AggregatedCommoditySourceRegion,
    ChangeSetCommoditySourceRead,
    CommodityBreakdownEntry,
    CommoditySourceSummary,
)
from src.backend.app.util.change_set import change_set_query
from src.backend.app.util.change_set_export import (
    MAX_ALIVE_ENTITIES,
    effective_export_rows_subquery,
    exported_rows_for_changeset_subquery,
)
from src.backend.app.util.enums import AdminRegionLevel, EntityScope, SortOrder
from src.backend.app.util.pagination import (
    PaginationCursor,
    Paginator,
    sort_with_tiebreak,
)


@dataclass(frozen=True)
class _CommodityExportDisplay:
    sourcing_country_name: str | None = None
    sourcing_administrative_level_1_name: str | None = None
    quantity_kilograms: float | None = None
    spend: float | None = None
    alive_in_change_set: bool = False


def _commodity_location_entities_query(
    change_set_uid: uuid.UUID,
    org_uid: uuid.UUID,
    scope: EntityScope = EntityScope.ALIVE,
) -> Select[Any]:
    """CommodityLocationEntity rows alive in this changeset, or - under
    `EntityScope.ALL` - every entity in the org, so a caller listing entities
    outside the changeset can still derive their values.
    """
    if scope is EntityScope.ALL:
        return select(CommodityLocationEntity).where(
            CommodityLocationEntity.org_uid == org_uid
        )
    return change_set_query(
        change_set_uid, org_uid, CommodityLocationEntity
    ).where(CommodityLocationEntity.org_uid == org_uid)


def _empty_commodity_summary(
    supplier_names: list[str],
    product_names: list[str],
) -> CommoditySourceSummary:
    """Zeroed summary for an entity set that resolves no exported rows.

    Supplier and product names come off the entity rows themselves, so they
    survive even when nothing resolves an ExportedCommodityLocation.
    """
    return CommoditySourceSummary(
        total_commodities=0,
        commodity_types=[],
        commodity_subgroups=[],
        sourcing_countries=[],
        sourcing_regions=[],
        supplier_names=supplier_names,
        product_names=product_names,
        total_suppliers=len(supplier_names),
        total_locations=0,
        total_spend=None,
        total_quantity=None,
        all_commodities_have_quantity=None,
        all_commodities_have_spend=None,
        missing_quantity_count=0,
        missing_spend_count=0,
        total_commodity_sources=0,
    )


def get_commodity_summary(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
    scope: EntityScope = EntityScope.ALIVE,
) -> CommoditySourceSummary:
    """
    Changeset-aware commodity source summary.

    Aggregates statistics from alive CommodityLocationEntity records, then
    separately aggregates over each entity's ExportedCommodityLocation row
    current as of this changeset.

    `scope=all` widens the entity set from the changeset's own entities to
    every entity in the org, and resolves each one's export row with a
    most-recent fallback. It exists so a caller listing entities outside the
    changeset can offer filter values that its rows can actually match;
    under it the figures describe that wider set too.
    """
    entities = (
        _commodity_location_entities_query(change_set_uid, org_uid, scope)
        .with_only_columns(
            CommodityLocationEntity.uid,
            CommodityLocationEntity.supplier,
            CommodityLocationEntity.product,
        )
        .subquery("commodity_entities")
    )
    export_columns = (
        ExportedCommodityLocation.entity_uid,
        ExportedCommodityLocation.commodity_type,
        ExportedCommodityLocation.commodity_subgroup,
        ExportedCommodityLocation.sourcing_country_name,
        ExportedCommodityLocation.sourcing_administrative_level_1_name,
        ExportedCommodityLocation.spend,
        ExportedCommodityLocation.quantity_kilograms,
    )
    commodities: Subquery
    if scope is EntityScope.ALL:
        # Entities outside the changeset resolve no changeset-current row, so
        # fall back to their most recent one rather than contributing nothing
        # to the value lists.
        commodities = effective_export_rows_subquery(
            ExportedCommodityLocation,
            change_set_uid,
            org_uid,
            columns=export_columns,
            restrict_to_uids=select(entities.c.uid),
            name="commodities_for_changeset",
        )
    else:
        commodities = exported_rows_for_changeset_subquery(
            ExportedCommodityLocation,
            change_set_uid,
            org_uid,
            columns=export_columns,
            restrict_to_uids=select(entities.c.uid),
            name="commodities_for_changeset",
        )

    # An entity with no resolved ExportedCommodityLocation row is all-NULL on
    # the outer join: it makes "all have quantity/spend" False and counts
    # towards neither missing-value count.
    resolved = commodities.c.entity_uid.isnot(None)
    result = safe_session.execute(
        select(
            func.count().label("entity_count"),
            func.count(commodities.c.entity_uid).label("resolved_count"),
            func.count(distinct(commodities.c.commodity_subgroup)).label(
                "total_commodities"
            ),
            func.count(distinct(commodities.c.sourcing_country_name)).label(
                "total_locations"
            ),
            func.sum(commodities.c.spend).label("total_spend"),
            func.sum(commodities.c.quantity_kilograms).label("total_quantity"),
            func.bool_and(commodities.c.quantity_kilograms.isnot(None)).label(
                "all_have_quantity"
            ),
            func.bool_and(commodities.c.spend.isnot(None)).label(
                "all_have_spend"
            ),
            func.count()
            .filter(resolved, commodities.c.quantity_kilograms.is_(None))
            .label("missing_quantity_count"),
            func.count()
            .filter(resolved, commodities.c.spend.is_(None))
            .label("missing_spend_count"),
            # Distinct value lists for FE filter dropdowns.
            array_agg(distinct(commodities.c.commodity_type)).label(
                "commodity_types"
            ),
            array_agg(distinct(commodities.c.commodity_subgroup)).label(
                "commodity_subgroups"
            ),
            array_agg(distinct(commodities.c.sourcing_country_name)).label(
                "sourcing_countries"
            ),
            array_agg(
                distinct(commodities.c.sourcing_administrative_level_1_name)
            ).label("sourcing_regions"),
            array_agg(distinct(entities.c.supplier)).label("supplier_names"),
            array_agg(distinct(entities.c.product)).label("product_names"),
        ).select_from(
            entities.outerjoin(
                commodities, commodities.c.entity_uid == entities.c.uid
            )
        )
    ).one()

    def filter_nulls(values: list[str | None]) -> list[str]:
        return sorted({v for v in values if v is not None})

    supplier_names = filter_nulls(result.supplier_names or [])
    product_names = filter_nulls(result.product_names or [])

    if result.entity_count == 0 or (
        scope is EntityScope.ALL and result.resolved_count == 0
    ):
        # Nothing to aggregate or offer as a filter value. Under
        # EntityScope.ALL an entity set resolving no row at all also leaves
        # the has-quantity/spend flags unknown rather than False.
        return _empty_commodity_summary(supplier_names, product_names)

    return CommoditySourceSummary(
        total_commodities=result.total_commodities,
        commodity_types=filter_nulls(result.commodity_types or []),
        commodity_subgroups=filter_nulls(result.commodity_subgroups or []),
        sourcing_countries=filter_nulls(result.sourcing_countries or []),
        sourcing_regions=filter_nulls(result.sourcing_regions or []),
        supplier_names=supplier_names,
        product_names=product_names,
        total_suppliers=len(supplier_names),
        total_locations=result.total_locations,
        total_spend=(
            int(result.total_spend) if result.total_spend is not None else None
        ),
        total_quantity=result.total_quantity,
        all_commodities_have_quantity=bool(result.all_have_quantity),
        all_commodities_have_spend=bool(result.all_have_spend),
        missing_quantity_count=result.missing_quantity_count,
        missing_spend_count=result.missing_spend_count,
        total_commodity_sources=result.resolved_count,
    )


_EXPORT_SORT_FIELDS = (
    "sourcing_country_name",
    "sourcing_administrative_level_1_name",
    "spend",
    "quantity_kilograms",
)

# The subset of the above that is numeric rather than text. These need an
# explicit cast wherever they come off a VALUES clause; the text ones do not.
_EXPORT_NUMERIC_SORT_FIELDS = ("spend", "quantity_kilograms")

# Sort keys are named after the response fields (CommodityLocationSortKey).
# The two whose column is spelled differently map here; every other key is
# its own column name.
_SORT_COLUMNS: dict[CommodityLocationSortKey, str] = {
    "sourcing_country": "sourcing_country_name",
    "sourcing_region": "sourcing_administrative_level_1_name",
}


def _apply_commodity_export_join(
    query: Select[Any],
    change_set_uid: uuid.UUID,
    org_uid: uuid.UUID,
    listed_uids_subq: Subquery,
    countries: list[str] | None,
    sourcing_administrative_level_1_names: list[str] | None,
    sort_columns: list[str],
) -> tuple[Select[Any], dict[str, ColumnElement[Any]] | None]:
    """Join each listed entity's effective ExportedCommodityLocation row
    into `query`, applying countries/regions filters and an extra sort column
    for each of `sort_columns` that is an export field.

    `listed_uids_subq` is the uid universe the outer query can return: the
    changeset's alive entities under `EntityScope.ALIVE`, every org entity
    under `EntityScope.ALL`. Resolving over that set rather than over the
    alive set alone is what lets a filter or sort behave the same for rows
    that are not in the selected version - otherwise filtering by country
    would silently drop every such row.

    Split out of `get_commodity_sources` to keep it under the complexity
    limit.
    """
    commodities = effective_export_rows_subquery(
        ExportedCommodityLocation,
        change_set_uid,
        org_uid,
        columns=(
            ExportedCommodityLocation.entity_uid,
            ExportedCommodityLocation.sourcing_country_name,
            ExportedCommodityLocation.sourcing_administrative_level_1_name,
            ExportedCommodityLocation.spend,
            ExportedCommodityLocation.quantity_kilograms,
        ),
        restrict_to_uids=select(listed_uids_subq.c.uid),
        name="commodities_for_listing",
    )
    query = query.outerjoin(
        commodities, commodities.c.entity_uid == CommodityLocationEntity.uid
    )
    if countries:
        query = query.where(commodities.c.sourcing_country_name.in_(countries))
    if sourcing_administrative_level_1_names:
        query = query.where(
            commodities.c.sourcing_administrative_level_1_name.in_(
                sourcing_administrative_level_1_names
            )
        )
    extra_sort_columns: dict[str, ColumnElement[Any]] = {}
    for sort_on in sort_columns:
        if sort_on not in _EXPORT_SORT_FIELDS:
            continue
        # An entity with no export row is NULL here. Callers passing an
        # expression own its NULLs, otherwise the keyset comparison hits
        # NULL and page two comes back empty. Sentinels match Paginator's
        # own: -inf for a number, "" for text.
        sort_column = func.coalesce(
            commodities.c[sort_on],
            float("-inf") if sort_on in _EXPORT_NUMERIC_SORT_FIELDS else "",
        )
        query = query.add_columns(sort_column.label(f"_extra_{sort_on}"))
        extra_sort_columns[sort_on] = sort_column
    return query, extra_sort_columns or None


def get_commodity_sources(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
    commodity_subgroup: str | None = None,
    commodity_subgroups: list[str] | None = None,
    countries: list[str] | None = None,
    sourcing_administrative_level_1_names: list[str] | None = None,
    suppliers: list[str] | None = None,
    product_names: list[str] | None = None,
    scope: EntityScope = EntityScope.ALIVE,
    sort_on: CommodityLocationSortKey = "identifier",
    sort_order: SortOrder = SortOrder.DESC,
    cursor: PaginationCursor | None = None,
    reverse_pagination: bool = False,
    limit: int = settings.DEFAULT_PAGE_SIZE,
) -> tuple[list[ChangeSetCommoditySourceRead], Paginator]:
    """
    Changeset-aware, paginated commodity source list.

    `scope=alive` (the default) returns the entities alive in this changeset.
    `scope=all` returns every CommodityLocationEntity in the org, each
    carrying `alive_in_change_set`, so a caller can show the rest as not in
    this version rather than omitting them.

    Display values come from each entity's ExportedCommodityLocation row
    current as of this changeset, or - for an entity with no such row - its
    most recent one. An entity with no ExportedCommodityLocation at all is
    still returned, with those fields null.

    `sort_on` is a response-field name; see _SORT_COLUMNS for the mapping to
    its column.
    """
    sort_column = _SORT_COLUMNS.get(sort_on, sort_on)

    query = _commodity_location_entities_query(change_set_uid, org_uid, scope)

    if commodity_subgroup:
        query = query.where(
            CommodityLocationEntity.commodity_subgroup.ilike(
                f"%{commodity_subgroup}%"
            )
        )
    if commodity_subgroups:
        query = query.where(
            CommodityLocationEntity.commodity_subgroup.in_(commodity_subgroups)
        )
    if suppliers:
        query = query.where(CommodityLocationEntity.supplier.in_(suppliers))
    if product_names:
        query = query.where(CommodityLocationEntity.product.in_(product_names))

    # The uid universe the export join must cover: every row this listing
    # can return, not just the alive ones. Projected before the filters below
    # so a filter cannot narrow the set its own join is resolved over.
    listed_uids_subq = query.with_only_columns(
        CommodityLocationEntity.uid
    ).subquery("listed_commodity_location_uids")

    # Many sources share a commodity, so break ties on the columns the list
    # shows (country, region, supplier, product), then the template's own ID.
    sort_columns, sort_orders = sort_with_tiebreak(
        sort_column,
        sort_order,
        "sourcing_country_name",
        "sourcing_administrative_level_1_name",
        "supplier",
        "product",
        "identifier",
    )

    # countries/sourcing_administrative_level_1_names live only on the
    # entity's effective ExportedCommodityLocation row
    # (CommodityLocationEntity has no such columns), so filtering or sorting
    # by them - which the tiebreaks above always do - or by spend/quantity
    # needs that same row joined in as extra sort columns.
    query, extra_sort_columns = _apply_commodity_export_join(
        query,
        change_set_uid,
        org_uid,
        listed_uids_subq,
        countries,
        sourcing_administrative_level_1_names,
        sort_columns,
    )

    paginator = CommodityLocationEntity.paginate(
        safe_session,
        query,
        sort_on=sort_columns,
        sort_order=sort_orders,
        cursor=cursor,
        limit=limit,
        reverse=reverse_pagination,
        extra_sort_columns=extra_sort_columns,
    )

    page_entities: list[CommodityLocationEntity] = list(paginator.results)  # type: ignore[arg-type]
    display_by_uid = _commodity_page_display(
        safe_session,
        change_set_uid,
        org_uid,
        scope,
        [entity.uid for entity in page_entities],
    )

    sources: list[ChangeSetCommoditySourceRead] = []
    for entity in page_entities:
        display = display_by_uid[entity.uid]
        sources.append(
            ChangeSetCommoditySourceRead(
                entity_uid=entity.uid,
                org_uid=entity.org_uid,
                identifier=entity.identifier,
                commodity_type=entity.commodity_type,
                commodity_subgroup=entity.commodity_subgroup,
                commodity_code=entity.commodity_code,
                year_purchased=entity.year_purchased,
                sourcing_country=display.sourcing_country_name,
                sourcing_region=display.sourcing_administrative_level_1_name,
                quantity_kilograms=display.quantity_kilograms,
                spend=display.spend,
                supplier=entity.supplier,
                product=entity.product,
                alive_in_change_set=display.alive_in_change_set,
            )
        )

    return sources, paginator


def _commodity_page_display(
    safe_session: SafeSession,
    change_set_uid: uuid.UUID,
    org_uid: uuid.UUID,
    scope: EntityScope,
    page_uids: list[uuid.UUID],
) -> dict[uuid.UUID, _CommodityExportDisplay]:
    """The display values of a page of already-paginated entities: each
    one's effective ExportedCommodityLocation row (null fields for an entity
    with none) and, under `EntityScope.ALL`, whether it is alive in the
    changeset. Under `EntityScope.ALIVE` the listing is the alive set itself.
    """
    if not page_uids:
        return {}
    commodities = effective_export_rows_subquery(
        ExportedCommodityLocation,
        change_set_uid,
        org_uid,
        columns=(
            ExportedCommodityLocation.entity_uid,
            ExportedCommodityLocation.sourcing_country_name,
            ExportedCommodityLocation.sourcing_administrative_level_1_name,
            ExportedCommodityLocation.quantity_kilograms,
            ExportedCommodityLocation.spend,
        ),
        restrict_to_uids=page_uids,
        name="commodities_for_page",
    )
    alive_in_change_set: ColumnElement[bool] = (
        CommodityLocationEntity.uid.in_(
            _commodity_location_entities_query(
                change_set_uid, org_uid, EntityScope.ALIVE
            ).with_only_columns(CommodityLocationEntity.uid)
        )
        if scope is EntityScope.ALL
        else true()
    )
    rows = safe_session.execute(
        select(
            CommodityLocationEntity.uid,
            commodities.c.sourcing_country_name,
            commodities.c.sourcing_administrative_level_1_name,
            commodities.c.quantity_kilograms,
            commodities.c.spend,
            alive_in_change_set.label("alive_in_change_set"),
        )
        .outerjoin(
            commodities,
            commodities.c.entity_uid == CommodityLocationEntity.uid,
        )
        .where(CommodityLocationEntity.uid.in_(page_uids))
    ).all()
    return {
        row.uid: _CommodityExportDisplay(
            sourcing_country_name=row.sourcing_country_name,
            sourcing_administrative_level_1_name=(
                row.sourcing_administrative_level_1_name
            ),
            quantity_kilograms=row.quantity_kilograms,
            spend=row.spend,
            alive_in_change_set=row.alive_in_change_set,
        )
        for row in rows
    }


@dataclass
class _RegionTotals:
    admin_region_uid: uuid.UUID | None = None
    total_spend: float = 0.0
    total_quantity: float = 0.0
    by_subgroup: dict[str, list[float]] = field(default_factory=dict)


def get_aggregated_commodity_regions(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
    commodity_subgroups: list[str] | None = None,
    include_geometry: bool = False,
    group_by_country: bool = False,
) -> list[AggregatedCommoditySourceRegion]:
    """Changeset-aware commodity spend/quantity per sourcing location, with a
    per-subgroup breakdown — one row per location, so geometry is sent once.

    The location is the entity's `sourcing_admin_region_uid`: a REGION-level
    AdminRegion when the commodity named an admin-1 region, COUNTRY-level
    otherwise. An entity whose names resolved no AdminRegion falls back to
    its export row's country / admin-1 names and gets no geometry. Spend and
    quantity come from each entity's
    ExportedCommodityLocation row current as of this changeset; an entity
    with no such row contributes nothing, as in `get_commodity_summary`.

    `group_by_country` sums every location into its country: one row per
    country, with no admin-1 name and the COUNTRY-level AdminRegion's
    geometry, even when the country was only named through its regions.
    """
    entity_query = change_set_query(
        change_set_uid, org_uid, CommodityLocationEntity
    ).where(CommodityLocationEntity.org_uid == org_uid)
    if commodity_subgroups:
        entity_query = entity_query.where(
            CommodityLocationEntity.commodity_subgroup.in_(commodity_subgroups)
        )
    alive_uids = list(
        safe_session.execute(
            entity_query.with_only_columns(CommodityLocationEntity.uid).limit(
                MAX_ALIVE_ENTITIES
            )
        )
        .scalars()
        .all()
    )
    if not alive_uids:
        return []

    # Resolved against the entity subquery directly (the alive-uid query
    # above only guards the empty case). `change_set_query` names its chain
    # CTE per model, so this ExportedCommodityLocation walk and the
    # CommodityLocationEntity restrict subquery do not clash in one
    # statement; two walks over the same model would need a `cs_chain_name`.
    exported = exported_rows_for_changeset_subquery(
        ExportedCommodityLocation,
        change_set_uid,
        org_uid,
        columns=(
            ExportedCommodityLocation.entity_uid,
            ExportedCommodityLocation.sourcing_country_name,
            ExportedCommodityLocation.sourcing_administrative_level_1_name,
            ExportedCommodityLocation.spend,
            ExportedCommodityLocation.quantity_kilograms,
        ),
        restrict_to_uids=entity_query.with_only_columns(
            CommodityLocationEntity.uid
        ),
        name="commodity_regions_for_changeset",
    )
    # The COUNTRY-level AdminRegion of the entity's region (itself, for a
    # COUNTRY row), which `group_by_country` locates every row at.
    country_region = aliased(AdminRegion)
    rows = safe_session.execute(
        select(
            CommodityLocationEntity.sourcing_admin_region_uid,
            country_region.uid.label("country_region_uid"),
            CommodityLocationEntity.commodity_subgroup,
            AdminRegion.country_name.label("region_country_name"),
            AdminRegion.name.label("region_name"),
            AdminRegion.level.label("region_level"),
            exported.c.sourcing_country_name,
            exported.c.sourcing_administrative_level_1_name,
            func.coalesce(func.sum(exported.c.spend), 0).label("total_spend"),
            func.coalesce(func.sum(exported.c.quantity_kilograms), 0).label(
                "total_quantity"
            ),
        )
        .select_from(exported)
        .join(
            CommodityLocationEntity,
            CommodityLocationEntity.uid == exported.c.entity_uid,
        )
        .outerjoin(
            AdminRegion,
            AdminRegion.uid
            == CommodityLocationEntity.sourcing_admin_region_uid,
        )
        .outerjoin(
            country_region,
            and_(
                country_region.level == AdminRegionLevel.COUNTRY,
                country_region.country_code == AdminRegion.country_code,
            ),
        )
        .group_by(
            CommodityLocationEntity.sourcing_admin_region_uid,
            country_region.uid,
            CommodityLocationEntity.commodity_subgroup,
            AdminRegion.country_name,
            AdminRegion.name,
            AdminRegion.level,
            exported.c.sourcing_country_name,
            exported.c.sourcing_administrative_level_1_name,
        )
    ).all()

    locations: dict[tuple[str, str | None], _RegionTotals] = {}
    for row in rows:
        if row.sourcing_admin_region_uid is not None:
            country_name = row.region_country_name
            admin_1_name = (
                row.region_name
                if row.region_level == AdminRegionLevel.REGION
                else None
            )
        else:
            country_name = row.sourcing_country_name
            admin_1_name = row.sourcing_administrative_level_1_name or None
        if country_name is None:
            continue
        region_uid = row.sourcing_admin_region_uid
        if group_by_country:
            admin_1_name = None
            region_uid = row.country_region_uid
        totals = locations.setdefault(
            (country_name, admin_1_name), _RegionTotals()
        )
        if totals.admin_region_uid is None:
            totals.admin_region_uid = region_uid
        spend, quantity = float(row.total_spend), float(row.total_quantity)
        totals.total_spend += spend
        totals.total_quantity += quantity
        subgroup = totals.by_subgroup.setdefault(
            row.commodity_subgroup, [0.0, 0.0]
        )
        subgroup[0] += spend
        subgroup[1] += quantity

    geometry_by_region_uid: dict[uuid.UUID, Any] = {}
    region_uids = {
        t.admin_region_uid
        for t in locations.values()
        if t.admin_region_uid is not None
    }
    if include_geometry and region_uids:
        geometry_by_region_uid = {
            row.uid: row.geometry
            for row in safe_session.execute(
                select(
                    AdminRegion.uid,
                    func.coalesce(
                        AdminRegion.geojson_simplified, AdminRegion.geojson
                    ).label("geometry"),
                ).where(AdminRegion.uid.in_(region_uids))
            )
        }

    # By country, a country-level row after its admin-1 regions.
    ordered = sorted(
        locations.items(),
        key=lambda item: (item[0][0], item[0][1] is None, item[0][1] or ""),
    )
    return [
        AggregatedCommoditySourceRegion(
            country_name=country_name,
            sourcing_administrative_level_1_name=admin_1_name,
            total_spend=totals.total_spend,
            total_quantity=totals.total_quantity,
            geometry=(
                geometry_by_region_uid.get(totals.admin_region_uid)
                if totals.admin_region_uid is not None
                else None
            ),
            commodity_breakdown=[
                CommodityBreakdownEntry(
                    commodity_subgroup=subgroup,
                    total_spend=spend,
                    total_quantity=quantity,
                )
                for subgroup, (spend, quantity) in sorted(
                    totals.by_subgroup.items()
                )
            ],
        )
        for (country_name, admin_1_name), totals in ordered
    ]
