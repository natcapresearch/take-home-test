import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    case,
    func,
    select,
    update,
)
from sqlalchemy.orm import aliased
from src.backend.app.access import SafeSession
from src.backend.app.config import settings
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
from src.backend.app.models.organisation import Organisation
from src.backend.app.schemas.change_set import (
    ChangeSetRead,
    ChangeSetSummary,
    ParentChangeSet,
    UnitOfAnalysisChangeSummary,
    UnitOfAnalysisChangeSummaryBreakdown,
)
from src.backend.app.schemas.organisation import OrganisationDB
from src.backend.app.util.change_set import (
    change_set_query,
    get_commodity_spend_coverage,
)
from src.backend.app.util.change_set_export import (
    MAX_ALIVE_ENTITIES,
    exported_rows_for_changeset_subquery,
)
from src.backend.app.util.enums import (
    ChangeSetState,
    SortOrder,
    UnitOfAnalysis,
)
from src.backend.app.util.pagination import PaginationCursor, Paginator

logger = settings.logger

_ALLOWED_STATE_TRANSITIONS: dict[ChangeSetState, set[ChangeSetState]] = {
    ChangeSetState.DRAFT: {ChangeSetState.PROCESSING},
    ChangeSetState.PROCESSING: {ChangeSetState.DRAFT, ChangeSetState.DONE},
    ChangeSetState.DONE: {ChangeSetState.PUBLISHED},
    ChangeSetState.PUBLISHED: {ChangeSetState.DONE},
}


def latest_change_set_uid(
    safe_session: SafeSession, org_uid: uuid.UUID
) -> uuid.UUID | None:
    """The leaf change set's uid, for read paths that only need to label it.

    The tolerant counterpart to `get_latest_change_set`, which raises when an
    organisation has more than one leaf. That strictness is right for a write
    — refusing to guess which version an edit belongs to — but wrong for a
    listing, where it would turn a merely odd change set tree into a 500 and
    take the whole page down. Picks the newest leaf deterministically instead,
    matching how the rest of the changeset code breaks ties.

    For the single-chain shape every healthy organisation has, this returns
    exactly what `get_latest_change_set` returns.
    """
    child = aliased(ChangeSet)
    return safe_session.execute(
        select(ChangeSet.uid)
        .outerjoin(child, child.parent_uid == ChangeSet.uid)
        .where(ChangeSet.org_uid == org_uid)
        .where(child.uid.is_(None))
        .order_by(ChangeSet.created_at.desc(), ChangeSet.uid.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_change_set(
    safe_session: SafeSession,
    org: OrganisationDB,
    change_set_uid: uuid.UUID | None = None,
) -> ChangeSetRead | None:
    """Get a change set by UID, or fall back to the organisation's default."""
    if change_set_uid is None:
        if org.default_change_set_uid is None:
            return None
        change_set_uid = org.default_change_set_uid

    result = safe_session.execute(
        select(ChangeSet)
        .where(ChangeSet.uid == change_set_uid)
        .where(ChangeSet.org_uid == org.uid)
    ).scalar_one_or_none()

    if result is None:
        return None

    return hydrate_change_set_reads(
        safe_session,
        org_uid=org.uid,
        change_sets=[result],
    )[0]


def get_change_sets(
    safe_session: SafeSession,
    org: OrganisationDB,
    state: ChangeSetState | None = None,
    visible_states: set[ChangeSetState] | None = None,
    cursor: PaginationCursor | None = None,
    reverse_pagination: bool = False,
    sort_on: str = "created_at",
    sort_order: SortOrder = SortOrder.DESC,
    limit: int = settings.DEFAULT_PAGE_SIZE,
) -> tuple[list[ChangeSetRead], Paginator]:
    """Return a paginated list of change sets belonging to the given org."""
    query = select(ChangeSet).where(ChangeSet.org_uid == org.uid)

    if state is not None:
        query = query.where(ChangeSet.state == state)

    if visible_states is not None:
        query = query.where(ChangeSet.state.in_(visible_states))

    paginator = ChangeSet.paginate(
        safe_session,
        query,
        sort_on,
        sort_order,
        cursor=cursor,
        limit=limit,
        reverse=reverse_pagination,
    )

    change_sets = hydrate_change_set_reads(
        safe_session,
        org_uid=org.uid,
        change_sets=list(paginator.results),
    )

    return change_sets, paginator


def hydrate_change_set_reads(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    change_sets: list[ChangeSet],
) -> list[ChangeSetRead]:
    """Hydrate ChangeSetRead payloads with a compact parent change set object
    and an `is_latest` flag.

    Parents already present in ``change_sets`` are reused directly; only missing
    parents are looked up in one batched query.

    `is_latest` is resolved against the organisation's true leaf, not against
    the rows being hydrated: a caller who cannot see the leaf must not have
    the newest change set they *can* see mislabelled as the latest, because
    that is precisely the case where editing has to be refused.
    """
    if not change_sets:
        return []

    leaf_uid = latest_change_set_uid(safe_session, org_uid)

    change_sets_by_uid: dict[uuid.UUID, ChangeSet] = {}
    parent_names_by_uid: dict[uuid.UUID, str | None] = {}
    for change_set in change_sets:
        change_sets_by_uid[change_set.uid] = change_set
        parent_names_by_uid[change_set.uid] = change_set.name

    missing_parent_uids = {
        change_set.parent_uid
        for change_set in change_sets
        if change_set.parent_uid is not None
        and change_set.parent_uid not in change_sets_by_uid
    }

    if missing_parent_uids:
        parent_rows = safe_session.execute(
            select(ChangeSet.uid, ChangeSet.name)
            .where(ChangeSet.org_uid == org_uid)
            .where(ChangeSet.uid.in_(missing_parent_uids))
        ).all()
        parent_names_by_uid.update(
            {parent_row.uid: parent_row.name for parent_row in parent_rows}
        )

    hydrated_change_sets: list[ChangeSetRead] = []
    for change_set in change_sets:
        parent_change_set = None
        if (
            change_set.parent_uid is not None
            and change_set.parent_uid in parent_names_by_uid
        ):
            parent_change_set = ParentChangeSet(
                uid=change_set.parent_uid,
                name=parent_names_by_uid[change_set.parent_uid],
            )

        change_set_read = ChangeSetRead.model_validate(change_set)
        change_set_read.parent_change_set = parent_change_set
        change_set_read.is_latest = change_set.uid == leaf_uid
        change_set_read.commodity_spend_coverage = get_commodity_spend_coverage(
            change_set
        )
        hydrated_change_sets.append(change_set_read)

    return hydrated_change_sets


def patch_change_set(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
    new_state: ChangeSetState | None = None,
) -> ChangeSet:
    """Update the name, description, and/or state of a change set.

    Name and description may be set independently of each other and of the
    state. When ``new_state`` is provided, the transition must be one of
    ``_ALLOWED_STATE_TRANSITIONS``.

    Raises ChangeSetNotFoundError if the change set is not found, does not belong to the
    organisation, or ChangeSetProcessingError if a requested state transition is not
    allowed.
    """
    change_set = safe_session.execute(
        select(ChangeSet)
        .where(ChangeSet.uid == change_set_uid)
        .where(ChangeSet.org_uid == org_uid)
    ).scalar_one_or_none()

    if change_set is None:
        raise ChangeSetNotFoundError(
            f"Change set {change_set_uid} not found for organisation {org_uid}"
        )

    if name is not None:
        change_set.name = name

    if description is not None:
        change_set.description = description

    if new_state is not None:
        previous_state = change_set.state
        allowed_targets = _ALLOWED_STATE_TRANSITIONS.get(change_set.state)
        if allowed_targets is None or new_state not in allowed_targets:
            raise ChangeSetProcessingError(
                f"Cannot transition change set from {change_set.state.value!r} to"
                f" {new_state.value!r}"
            )
        change_set.state = new_state

        if (
            new_state == ChangeSetState.PROCESSING
            and change_set.description is None
        ):
            change_set.description = exported_rows_description(
                safe_session, org_uid, change_set_uid
            )

        if new_state == ChangeSetState.PUBLISHED:
            change_set.published_at = datetime.now(timezone.utc)
            change_set.unpublished_at = None
        elif (
            previous_state == ChangeSetState.PUBLISHED
            and new_state == ChangeSetState.DONE
        ):
            change_set.published_at = None
            change_set.unpublished_at = datetime.now(timezone.utc)

        if (
            new_state == ChangeSetState.PUBLISHED
            or previous_state == ChangeSetState.PUBLISHED
        ):
            _sync_default_change_set_uid_to_newest_published(
                safe_session, org_uid
            )

    safe_session.commit()

    return change_set


def _coverage(with_value: int, total: int) -> str:
    if with_value == total:
        return "full"
    if with_value == 0:
        return "missing"
    return "partial"


def exported_rows_description(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
) -> str | None:
    """Describe the exported rows recorded in this change set alone.

    "111 commodity sources. Commodity quantity: full. Commodity spend:
    missing", counted from the exported_commodity_location rows a change of
    the change set points at (change.new_uid). Ancestor change sets are not
    looked at. Returns None when there are no commodity sources.
    """
    commodity_sources, with_quantity, with_spend = safe_session.execute(
        select(
            func.count(ExportedCommodityLocation.uid.distinct()),
            func.count(ExportedCommodityLocation.uid.distinct()).filter(
                ExportedCommodityLocation.quantity_kilograms.is_not(None)
            ),
            func.count(ExportedCommodityLocation.uid.distinct()).filter(
                ExportedCommodityLocation.spend.is_not(None)
            ),
        )
        .join(Change, Change.new_uid == ExportedCommodityLocation.uid)
        .where(
            Change.change_set_uid == change_set_uid,
            Change.org_uid == org_uid,
            Change.model_type == ExportedCommodityLocation.__tablename__,
            ExportedCommodityLocation.org_uid == org_uid,
        )
    ).one()

    if commodity_sources == 0:
        return None

    commodity_word = (
        "commodity source" if commodity_sources == 1 else "commodity sources"
    )
    parts = [
        f"{commodity_sources} {commodity_word}",
        f"Commodity quantity: {_coverage(with_quantity, commodity_sources)}",
        f"Commodity spend: {_coverage(with_spend, commodity_sources)}",
    ]
    return ". ".join(parts)


def regenerate_unedited_description(
    safe_session: SafeSession,
    change_set: ChangeSet,
    description_before: str | None,
) -> None:
    """Bring the generated description of a draft up to date with its rows.

    `description_before` is `exported_rows_description` as it was before the
    draft's rows were replaced. A stored description equal to it was never
    edited, so it is regenerated; a description typed by hand, or none yet,
    is left alone.
    """
    if (
        change_set.description is None
        or change_set.description != description_before
    ):
        return
    change_set.description = exported_rows_description(
        safe_session, change_set.org_uid, change_set.uid
    )


def _sync_default_change_set_uid_to_newest_published(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
) -> None:
    """Set organisation.default_change_set_uid to the newest PUBLISHED change set
    (ordered by created_at DESC, uid DESC), or NULL when none exist.

    Must be called inside the same transaction as the publish/unpublish operation
    so the read reflects the updated state.
    """
    newest_published_uid = safe_session.execute(
        select(ChangeSet.uid)
        .where(ChangeSet.org_uid == org_uid)
        .where(ChangeSet.state == ChangeSetState.PUBLISHED)
        .order_by(ChangeSet.created_at.desc(), ChangeSet.uid.desc())
        .limit(1)
    ).scalar_one_or_none()

    safe_session.execute(
        update(Organisation)
        .where(Organisation.uid == org_uid)
        .values(default_change_set_uid=newest_published_uid)
    )


def _summaries_from_rows(
    rows: Sequence[Any],
) -> list[UnitOfAnalysisChangeSummary]:
    """Turn `(grouping, num_rows)` rows into the breakdown's summary list.

    `value` is each group's *share* of the rows, not its count — the field
    has always been a fraction, and the frontend reads list length rather
    than value, so keep both paths emitting the same thing.
    """
    total_count = sum(row.num_rows for row in rows)
    return [
        UnitOfAnalysisChangeSummary(
            value=(
                row.num_rows / total_count
                if total_count > 0
                else float(row.num_rows)
            ),
            text=row.grouping or "unknown",
        )
        for row in rows
    ]


def _set_breakdown(
    unit_of_analysis_summaries: dict[
        UnitOfAnalysis, UnitOfAnalysisChangeSummaryBreakdown
    ],
    unit_of_analysis: UnitOfAnalysis,
    breakdown_key: str,
    rows: Sequence[Any],
) -> None:
    if not rows:
        return
    breakdown = unit_of_analysis_summaries.setdefault(
        unit_of_analysis,
        UnitOfAnalysisChangeSummaryBreakdown(),
    )
    setattr(breakdown, breakdown_key, _summaries_from_rows(rows))


def _alive_entity_uids(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
    model: type[BaseModel],
) -> list[uuid.UUID]:
    """Entity uids alive as of `change_set_uid`, materialised as a list.

    Materialised rather than left as a subquery so the uids are bounded to
    `MAX_ALIVE_ENTITIES`, gated with a presence check, and reused across the
    several grouped-count queries below. `change_set_query` names its
    recursive CTE per model, so nesting this inside
    `exported_rows_for_changeset_subquery` (a different model) would not
    clash anyway; two walks over the same model would, and one would then
    need a different `cs_chain_name`.
    """
    alive = (
        change_set_query(change_set_uid, org_uid, model)
        .where(model.org_uid == org_uid)
        .subquery()
    )
    return list(
        safe_session.execute(select(alive.c.uid).limit(MAX_ALIVE_ENTITIES))
        .scalars()
        .all()
    )


def _grouped_counts(
    safe_session: SafeSession,
    grouping: Any,
    source: Any,
    group_by: Sequence[Any] | None = None,
) -> Sequence[Any]:
    """Run one `SELECT <grouping>, COUNT(*) ... GROUP BY <grouping>`.

    One statement per grouping: each reads a different column.
    """
    return safe_session.execute(
        select(
            grouping.label("grouping"),
            func.count().label("num_rows"),
        )
        .select_from(source)
        .group_by(*(group_by or [grouping]))
    ).all()


def _versioned_unit_of_analysis_summaries(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
) -> dict[UnitOfAnalysis, UnitOfAnalysisChangeSummaryBreakdown]:
    """Change-set summaries: what the version *contains*.

    Not the change rows a single change set owns: a summary scoped to one
    change set's own rows would ignore everything inherited from its
    ancestors.

    So this resolves the entities alive as of the change set and groups
    each one's `ExportedCommodityLocation` row current as of that same
    change set — the same set, resolved the same way, as the headline
    counts from `get_commodity_summary` that these figures sit beneath.
    """
    unit_of_analysis_summaries: dict[
        UnitOfAnalysis, UnitOfAnalysisChangeSummaryBreakdown
    ] = {}

    alive_commodity_uids = _alive_entity_uids(
        safe_session, org_uid, change_set_uid, CommodityLocationEntity
    )
    if alive_commodity_uids:
        commodities = exported_rows_for_changeset_subquery(
            ExportedCommodityLocation,
            change_set_uid,
            org_uid,
            columns=(
                ExportedCommodityLocation.entity_uid,
                ExportedCommodityLocation.commodity_type,
                ExportedCommodityLocation.sourcing_country_name,
                ExportedCommodityLocation.sourcing_administrative_level_1_name,
                ExportedCommodityLocation.supplier,
                ExportedCommodityLocation.product,
            ),
            restrict_to_uids=alive_commodity_uids,
            name="commodities_for_changeset_summary",
        )
        country = commodities.c.sourcing_country_name
        admin_1 = commodities.c.sourcing_administrative_level_1_name
        # "Country Admin1", or just "Country" when there's no admin-1 name.
        region_label = case(
            (admin_1.is_(None), country),
            else_=country + " " + admin_1,
        )
        for breakdown_key, grouping, group_by in (
            ("commodities", commodities.c.commodity_type, None),
            ("regions", region_label, [country, admin_1]),
            ("suppliers", commodities.c.supplier, None),
            ("products", commodities.c.product, None),
        ):
            _set_breakdown(
                unit_of_analysis_summaries,
                UnitOfAnalysis.COMMODITY_SOURCE,
                breakdown_key,
                _grouped_counts(safe_session, grouping, commodities, group_by),
            )

    return unit_of_analysis_summaries


def get_change_summary(
    safe_session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
) -> ChangeSetSummary:
    root_query = safe_session.execute(
        select(ChangeSet)
        .where(ChangeSet.org_uid == org_uid)
        .where(ChangeSet.uid == change_set_uid)
    ).scalar_one_or_none()

    if root_query is None:
        raise ChangeSetNotFoundError(
            f"Change set {change_set_uid} not found for organisation {org_uid}"
        )

    unit_of_analysis_summaries = _versioned_unit_of_analysis_summaries(
        safe_session, org_uid, change_set_uid
    )

    return ChangeSetSummary(
        org_uid=org_uid,
        change_set_uid=change_set_uid,
        state=root_query.state,
        name=root_query.name,
        description=root_query.description,
        unit_of_analysis_summaries=unit_of_analysis_summaries,
    )
