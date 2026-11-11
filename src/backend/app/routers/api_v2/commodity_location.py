from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from pydantic import UUID4, TypeAdapter
from src.backend.app import deps
from src.backend.app.access import Access, SafeSession
from src.backend.app.api.v2 import (
    commodity_location as commodity_location_api_v2,
)
from src.backend.app.models.organisation import Organisation
from src.backend.app.schemas.api_v2.commodity_location import (
    ChangeSetCommodityLocationQueryParams,
    ChangeSetCommodityRegionQueryParams,
)
from src.backend.app.schemas.commodity_source import (
    AggregatedCommoditySourceRegion,
    ChangeSetCommoditySourceRead,
    CommoditySourceSummary,
)
from src.backend.app.util import change_set as change_set_util
from src.backend.app.util.enums import EntityScope
from src.backend.app.util.pagination_headers import set_pagination_headers

commodity_location_api_v2_router = APIRouter(
    tags=["commodity-locations-api-v2"],
)

_aggregated_region_list_adapter: TypeAdapter[
    list[AggregatedCommoditySourceRegion]
] = TypeAdapter(list[AggregatedCommoditySourceRegion])


@commodity_location_api_v2_router.get(
    "/commodity-sources/",
    response_model=list[ChangeSetCommoditySourceRead],
    summary="Get changeset-aware list of commodity sources",
)
def get_commodity_sources(
    response: Response,
    q: Annotated[ChangeSetCommodityLocationQueryParams, Query()],
    safe_session: SafeSession = Depends(deps.get_safe_session),
    org: Organisation = Depends(deps.current_org),
    access: Access = Depends(deps.access),
) -> list[ChangeSetCommoditySourceRead]:
    """
    Get commodity sources for the given organisation scoped to a changeset.

    Sources data from CommodityLocationEntity + ExportedCommodityLocation.
    Supports cursor-based pagination via before/after.
    """
    change_set_util.get_visible_change_set_or_404(
        safe_session, access, org.uid, q.change_set_uid
    )

    sources, paginator = commodity_location_api_v2.get_commodity_sources(
        safe_session,
        org.uid,
        q.change_set_uid,
        commodity_subgroup=q.commodity_subgroup,
        commodity_subgroups=q.commodity_subgroups,
        countries=q.countries,
        sourcing_administrative_level_1_names=q.sourcing_administrative_level_1_names,
        suppliers=q.suppliers,
        product_names=q.product_names,
        scope=q.scope,
        sort_on=q.sort_on,
        sort_order=q.sort_order,
        cursor=q.before or q.after,
        reverse_pagination=bool(q.before),
        limit=q.limit,
    )

    set_pagination_headers(response, paginator)

    return sources


@commodity_location_api_v2_router.get(
    "/commodity-summary/",
    response_model=CommoditySourceSummary,
    summary="Get changeset-aware commodity source summary",
)
def get_commodity_summary(
    change_set_uid: UUID4 = Query(...),
    scope: EntityScope = Query(default=EntityScope.ALIVE),
    safe_session: SafeSession = Depends(deps.get_safe_session),
    org: Organisation = Depends(deps.current_org),
    access: Access = Depends(deps.access),
) -> CommoditySourceSummary:
    """
    Get aggregated summary statistics for commodity sources in a changeset.

    Sources data from CommodityLocationEntity + ExportedCommodityLocation.
    `scope=all` widens the entity set from the changeset's own entities to
    every one in the org, matching the `scope` on the listing endpoint, so a
    caller showing entities outside the changeset can offer filter values
    those rows can match.
    """
    change_set_util.get_visible_change_set_or_404(
        safe_session, access, org.uid, change_set_uid
    )

    return commodity_location_api_v2.get_commodity_summary(
        safe_session,
        org.uid,
        change_set_uid,
        scope,
    )


@commodity_location_api_v2_router.get(
    "/commodity-source-regions-aggregated/",
    response_model=list[AggregatedCommoditySourceRegion],
    summary="Get changeset-aware commodity sources aggregated by sourcing location",
)
def get_aggregated_commodity_regions(
    q: Annotated[ChangeSetCommodityRegionQueryParams, Query()],
    safe_session: SafeSession = Depends(deps.get_safe_session),
    org: Organisation = Depends(deps.current_org),
    access: Access = Depends(deps.access),
) -> Response:
    """
    Get commodity spend and quantity per sourcing location in a changeset,
    with a per-subgroup breakdown and the location's geometry sent once.

    Sources data from CommodityLocationEntity (location via its
    sourcing_admin_region_uid) + ExportedCommodityLocation (spend, quantity).
    """
    change_set_util.get_visible_change_set_or_404(
        safe_session, access, org.uid, q.change_set_uid
    )

    regions = commodity_location_api_v2.get_aggregated_commodity_regions(
        safe_session,
        org.uid,
        q.change_set_uid,
        commodity_subgroups=q.commodity_subgroups,
        include_geometry=q.include_geometry,
        group_by_country=q.group_by_country,
    )
    # Bypass FastAPI's jsonable_encoder (slow for large nested geometry
    # coordinates). response_model above is kept for OpenAPI docs only.
    return Response(
        content=_aggregated_region_list_adapter.dump_json(
            regions, by_alias=True
        ),
        media_type="application/json",
    )
