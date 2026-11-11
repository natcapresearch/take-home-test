import uuid

from sqlalchemy import (
    Select,
    func,
    literal,
    select,
)
from sqlalchemy.orm import aliased
from src.backend.app.access import Access, SafeSession
from src.backend.app.errors.errors import (
    ChangeSetNotFoundError,
    ChangeSetProcessingError,
)
from src.backend.app.models.base import BaseModel
from src.backend.app.models.change_set import Change, ChangeSet
from src.backend.app.models.commodity_location_entity import (
    CommodityLocationEntity,
)
from src.backend.app.models.export.exported_commodity_location import (
    ExportedCommodityLocation,
)
from src.backend.app.schemas.change_set import (
    ChangeSetDataShape,
    commodity_spend_coverage,
)
from src.backend.app.util.enums import (
    ChangeSetState,
    DataCoverage,
    is_completed_state,
)

NON_ADMIN_VISIBLE_CHANGE_SET_STATES = {
    ChangeSetState.DRAFT,
    ChangeSetState.PUBLISHED,
}


def can_read_all_change_set_states(access: Access) -> bool:
    return access.check("read:change_set:all", None)


def get_visible_change_set_or_404(
    safe_session: SafeSession,
    access: Access,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
) -> ChangeSet:
    """Get a change set the caller can see, or raise `ChangeSetNotFoundError`.

    A change set that doesn't exist, belongs to another org, or isn't visible
    to the caller's role all raise the same 404, so none can be told apart.
    Shared by v1 and v2 routers.
    """
    result = safe_session.execute(
        select(ChangeSet)
        .where(ChangeSet.uid == change_set_uid)
        .where(ChangeSet.org_uid == org_uid)
    ).scalar_one_or_none()

    if result is None or (
        not can_read_all_change_set_states(access)
        and result.state not in NON_ADMIN_VISIBLE_CHANGE_SET_STATES
    ):
        raise ChangeSetNotFoundError("Change set not found.")

    return result


def get_latest_change_set(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    create_if_needed: bool = False,
) -> ChangeSet | None:
    """Find the leaf change set for an organisation (the one with no children)."""
    child = aliased(ChangeSet)
    leaf_query = (
        select(ChangeSet)
        .outerjoin(child, child.parent_uid == ChangeSet.uid)
        .where(ChangeSet.org_uid == org_uid)
        .where(child.uid.is_(None))
        .limit(2)
    )
    results = safe_session.execute(leaf_query).scalars().all()

    if len(results) > 1:
        raise ValueError(
            f"Multiple leaf change sets found for organisation {org_uid}"
        )

    result = results[0] if results else None
    if create_if_needed:
        if result is not None and result.state == ChangeSetState.PROCESSING:
            raise ChangeSetProcessingError(
                f"Cannot update: change set {result.uid} is currently processing"
            )
        if result is None or is_completed_state(result.state):
            result = create_change_set(safe_session, org_uid)
            safe_session.flush()

    return result


def create_change_set(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
) -> ChangeSet:
    """Create a new change set in draft state for the given organisation."""
    latest = get_latest_change_set(safe_session, org_uid)

    if latest and not is_completed_state(latest.state):
        raise ValueError(
            f"Cannot create new change set: latest change set {latest.uid} is not in"
            f" completed state {latest.state}"
        )

    change_set = ChangeSet(
        org_uid=org_uid,
        parent_uid=latest.uid if latest else None,
        state=ChangeSetState.DRAFT,
    )
    safe_session.add(change_set)
    refresh_change_set_datashape(safe_session, change_set)

    return change_set


def compute_change_set_datashape(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
) -> ChangeSetDataShape:
    """Count the commodity locations alive as of a change set, and how many
    have spend on their exported row current as of it.

    Aliveness comes from the entity's change records, values from the
    exported row resolved through the change set's ancestor chain. Each
    `change_set_query` builds its own chain CTE, named per model unless
    `cs_chain_name` is passed; this fetches the alive uids before counting
    the exported rows rather than renaming one.
    """
    commodity_location_uids = list(
        safe_session.execute(
            change_set_query(change_set_uid, org_uid, CommodityLocationEntity)
            .where(CommodityLocationEntity.org_uid == org_uid)
            .with_only_columns(CommodityLocationEntity.uid)
        )
        .scalars()
        .all()
    )

    commodity_locations_with_spend = change_set_query(
        change_set_uid, org_uid, ExportedCommodityLocation
    ).where(
        ExportedCommodityLocation.org_uid == org_uid,
        ExportedCommodityLocation.entity_uid.in_(commodity_location_uids),
        ExportedCommodityLocation.spend.is_not(None),
    )
    commodity_locations_with_spend_count = (
        safe_session.scalar(
            commodity_locations_with_spend.with_only_columns(
                func.count(ExportedCommodityLocation.entity_uid.distinct())
            )
        )
        or 0
    )

    commodity_location_count = len(commodity_location_uids)
    return ChangeSetDataShape(
        commodity_location_count=commodity_location_count,
        commodity_locations_with_spend_count=commodity_locations_with_spend_count,
        full_commodity_spend_coverage=commodity_location_count > 0
        and commodity_locations_with_spend_count == commodity_location_count,
    )


def refresh_change_set_datashape(
    safe_session: SafeSession,
    change_set: ChangeSet,
) -> None:
    """Recompute and store `change_set.datashape` for a draft change set.

    Call it after every write that creates a draft or changes its commodity
    locations, inside the same transaction. A completed change set keeps the
    datashape it had when it left draft.
    """
    if change_set.state != ChangeSetState.DRAFT:
        raise ValueError(
            f"Cannot refresh datashape: change set {change_set.uid} is in"
            f" state {change_set.state}, expected draft"
        )

    # The change set's uid, and any rows just added to it, exist only once
    # flushed.
    safe_session.flush()
    change_set.datashape = compute_change_set_datashape(
        safe_session, change_set.org_uid, change_set.uid
    ).model_dump(by_alias=True)


def get_commodity_spend_coverage(
    change_set: ChangeSet,
) -> DataCoverage | None:
    """The change set's commodity spend coverage, from its stored datashape.
    None when it has no datashape."""
    if change_set.datashape is None:
        return None
    return commodity_spend_coverage(
        ChangeSetDataShape.model_validate(change_set.datashape)
    )


def create_change(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    change_set: ChangeSet,
    model_type: type[BaseModel],
    description: str,
    new_uid: uuid.UUID | None = None,
    previous_uid: uuid.UUID | None = None,
) -> Change:
    """Create a change and add it to the given draft change set.

    The caller must supply a change set in DRAFT state. Raises ValueError if
    the change set is not in draft state or does not belong to the organisation.

    If the previous_uid is none we will assume this is a new entity. If the new_uid
    is none we will assume this entity is being deleted. Both new_uid and previous_uid
    can be provided, in which case we will assume this entity is being updated.
    """

    if change_set.org_uid != org_uid:
        raise ValueError(
            f"Change set {change_set.uid} does not belong to organisation {org_uid}"
        )

    if change_set.state != ChangeSetState.DRAFT:
        raise ValueError(
            f"Cannot add change: change set {change_set.uid} is in"
            f" state {change_set.state}, expected draft"
        )

    change = Change(
        org_uid=org_uid,
        change_set_uid=change_set.uid,
        model_type=model_type.__tablename__,
        description=description,
        new_uid=new_uid,
        previous_uid=previous_uid,
    )
    safe_session.add(change)

    return change


def change_set_query(
    change_set_uid: uuid.UUID,
    org_uid: uuid.UUID,
    model: type[BaseModel],
    *,
    cs_chain_name: str | None = None,
) -> Select[tuple[BaseModel]]:
    # Step 1: walk the changeset parent chain (independent of changes).
    # Named per model so an entity listing and its export-row resolution can
    # share one statement: SQLAlchemy rejects two unrelated CTEs of the same
    # name in a compiled statement. Two queries over the same model can share
    # a statement only if one of them passes a different `cs_chain_name`.
    cs_top = (
        select(
            ChangeSet.uid,
            ChangeSet.parent_uid,
            literal(0).label("ordering_number"),
        )
        .where(ChangeSet.uid == change_set_uid)
        .cte(
            cs_chain_name or f"cs_chain_{model.__tablename__}",
            recursive=True,
        )
    )
    cs_bottom = select(
        ChangeSet.uid,
        ChangeSet.parent_uid,
        (cs_top.c.ordering_number + 1).label("ordering_number"),
    ).join(cs_top, cs_top.c.parent_uid == ChangeSet.uid)
    cs_chain = cs_top.union_all(cs_bottom)

    # Step 2: collect all relevant changes across the chain, tagged by depth.
    relevant_changes = (
        select(
            Change.new_uid,
            Change.previous_uid,
            cs_chain.c.ordering_number,
        )
        .join(cs_chain, Change.change_set_uid == cs_chain.c.uid)
        .where(Change.org_uid == org_uid)
        .where(Change.model_type == model.__tablename__)
        .subquery("relevant_changes")
    )

    # Step 3: every (change, model row) pair in the chain. A tombstone
    # (new_uid NULL) resolves the row it deleted through previous_uid.
    # A NULL matching column never resolved a row (it joined on `=`), so
    # those rows are excluded here, before they can form a window partition.
    matching_columns = model.__matching_columns__
    versions = (
        select(
            *matching_columns,
            model.uid.label("version_uid"),
            model.created_at.label("created_at"),
            relevant_changes.c.ordering_number,
            relevant_changes.c.new_uid,
        )
        .select_from(
            relevant_changes.join(
                model,
                model.uid
                == func.coalesce(
                    relevant_changes.c.new_uid,
                    relevant_changes.c.previous_uid,
                ),
            )
        )
        .where(*[col.is_not(None) for col in matching_columns])
        .subquery("versions")
    )
    # The matching columns come first in `versions`, as in the old grouping.
    partition = list(versions.c)[: len(matching_columns)]

    # Step 4: per entity, the nearest ancestor's ordering_number
    # (smallest = most recent in the chain) and the latest created_at.
    windowed = select(
        versions.c.version_uid,
        versions.c.created_at,
        versions.c.ordering_number,
        versions.c.new_uid,
        func.min(versions.c.ordering_number)
        .over(partition_by=partition)
        .label("nearest_ordering_number"),
        func.max(versions.c.created_at)
        .over(partition_by=partition)
        .label("latest_created_at"),
    ).subquery("windowed")

    # The row is alive if it is the latest version and the winning changeset
    # records it as created (new_uid = its own uid). Selected through IN so a
    # row recorded twice in one changeset is listed once.
    #
    # Not an EXISTS joined to a GROUP BY of the same changes: Postgres
    # unnests that into a join on ordering_number alone (a handful of
    # distinct values), which is quadratic in the number of changes.
    winners = select(windowed.c.version_uid).where(
        windowed.c.created_at == windowed.c.latest_created_at,
        windowed.c.ordering_number == windowed.c.nearest_ordering_number,
        windowed.c.new_uid == windowed.c.version_uid,
    )

    return select(model).where(model.uid.in_(winners))
