import uuid
from collections.abc import Callable
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from src.backend.app.access import SafeSession
from src.backend.app.api.v1.change_set import (
    get_change_set,
    get_change_sets,
    get_change_summary,
    hydrate_change_set_reads,
    patch_change_set,
)
from src.backend.app.errors.errors import (
    ChangeSetNotFoundError,
    ChangeSetProcessingError,
)
from src.backend.app.models.change_set import Change, ChangeSet
from src.backend.app.models.export.exported_commodity_location import (
    ExportedCommodityLocation,
)
from src.backend.app.models.organisation import Organisation
from src.backend.app.schemas.organisation import OrganisationDB
from src.backend.app.util.enums import (
    ChangeSetState,
    DataCoverage,
)


@pytest.fixture
def org_uid(
    make_org_orm: Callable[..., Organisation],
) -> uuid.UUID:
    org = make_org_orm()
    return org.uid


@pytest.fixture
def org_db(
    make_org_orm: Callable[..., Organisation],
    test_org: OrganisationDB,
) -> OrganisationDB:
    make_org_orm()
    return test_org


# ---------------------------------------------------------------------------
# get_change_set
# ---------------------------------------------------------------------------


def test_get_change_set_by_uid(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    cs = ChangeSet(org_uid=org_db.uid, state=ChangeSetState.DRAFT)
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = get_change_set(test_admin_session, org_db, cs.uid)
    assert result is not None
    assert result.uid == cs.uid


def test_get_change_set_includes_parent_change_set_details(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    parent = ChangeSet(
        org_uid=org_db.uid,
        state=ChangeSetState.DONE,
        name="Parent",
    )
    test_admin_session.add(parent)
    test_admin_session.flush()

    child = ChangeSet(
        org_uid=org_db.uid,
        parent_uid=parent.uid,
        state=ChangeSetState.DRAFT,
        name="Child",
    )
    test_admin_session.add(child)
    test_admin_session.flush()

    result = get_change_set(test_admin_session, org_db, child.uid)
    assert result is not None
    assert result.parent_uid == parent.uid
    assert result.parent_change_set is not None
    assert result.parent_change_set.uid == parent.uid
    assert result.parent_change_set.name == "Parent"


def test_get_change_set_returns_none_when_uid_not_found(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    result = get_change_set(test_admin_session, org_db, uuid.uuid4())
    assert result is None


def test_get_change_set_returns_none_when_uid_belongs_to_other_org(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
    make_org_orm: Callable[..., Organisation],
):
    other_org = OrganisationDB(
        uid=uuid.uuid4(),
        name="Other Org",
    )
    make_org_orm(other_org)

    cs = ChangeSet(org_uid=other_org.uid, state=ChangeSetState.DRAFT)
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = get_change_set(test_admin_session, org_db, cs.uid)
    assert result is None


def test_get_change_set_falls_back_to_default(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    cs = ChangeSet(org_uid=org_db.uid, state=ChangeSetState.PUBLISHED)
    test_admin_session.add(cs)
    test_admin_session.flush()

    org_db.default_change_set_uid = cs.uid

    result = get_change_set(test_admin_session, org_db)
    assert result is not None
    assert result.uid == cs.uid


def test_get_change_set_returns_none_when_no_default(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    org_db.default_change_set_uid = None

    result = get_change_set(test_admin_session, org_db)
    assert result is None


# ---------------------------------------------------------------------------
# get_change_sets
# ---------------------------------------------------------------------------


def test_get_change_sets_returns_empty_list_when_no_change_sets(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    change_sets, paginator = get_change_sets(test_admin_session, org_db)
    assert change_sets == []
    assert paginator.total_count == 0


def test_get_change_sets_returns_all_change_sets_for_org(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    cs1 = ChangeSet(org_uid=org_db.uid, state=ChangeSetState.DRAFT)
    cs2 = ChangeSet(org_uid=org_db.uid, state=ChangeSetState.PUBLISHED)
    test_admin_session.add_all([cs1, cs2])
    test_admin_session.flush()

    change_sets, paginator = get_change_sets(test_admin_session, org_db)
    assert len(change_sets) == 2
    assert paginator.total_count == 2


def test_get_change_sets_filters_by_state(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    cs1 = ChangeSet(org_uid=org_db.uid, state=ChangeSetState.DRAFT)
    cs2 = ChangeSet(org_uid=org_db.uid, state=ChangeSetState.PUBLISHED)
    cs3 = ChangeSet(org_uid=org_db.uid, state=ChangeSetState.DRAFT)
    test_admin_session.add_all([cs1, cs2, cs3])
    test_admin_session.flush()

    change_sets, _ = get_change_sets(
        test_admin_session, org_db, state=ChangeSetState.DRAFT
    )
    assert len(change_sets) == 2
    assert all(cs.state == ChangeSetState.DRAFT for cs in change_sets)


def test_get_change_sets_does_not_return_other_org_change_sets(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
    make_org_orm: Callable[..., Organisation],
):
    other_org = OrganisationDB(
        uid=uuid.uuid4(),
        name="Other Org",
    )
    make_org_orm(other_org)

    cs_other = ChangeSet(org_uid=other_org.uid, state=ChangeSetState.DRAFT)
    cs_own = ChangeSet(org_uid=org_db.uid, state=ChangeSetState.DRAFT)
    test_admin_session.add_all([cs_other, cs_own])
    test_admin_session.flush()

    change_sets, _ = get_change_sets(test_admin_session, org_db)
    assert len(change_sets) == 1
    assert change_sets[0].org_uid == org_db.uid


def test_get_change_sets_respects_limit(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    for _ in range(5):
        test_admin_session.add(
            ChangeSet(org_uid=org_db.uid, state=ChangeSetState.DRAFT)
        )
    test_admin_session.flush()

    change_sets, paginator = get_change_sets(
        test_admin_session, org_db, limit=2
    )
    assert len(change_sets) == 2
    assert paginator.total_count == 5


def test_get_change_sets_includes_parent_change_set_details(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    parent = ChangeSet(
        org_uid=org_db.uid,
        state=ChangeSetState.DONE,
        name="Parent",
    )
    test_admin_session.add(parent)
    test_admin_session.flush()

    child = ChangeSet(
        org_uid=org_db.uid,
        parent_uid=parent.uid,
        state=ChangeSetState.DRAFT,
        name="Child",
    )
    test_admin_session.add(child)
    test_admin_session.flush()

    change_sets, _ = get_change_sets(test_admin_session, org_db, limit=2)
    by_uid = {change_set.uid: change_set for change_set in change_sets}

    assert by_uid[child.uid].parent_uid == parent.uid
    assert by_uid[child.uid].parent_change_set is not None
    child_parent = by_uid[child.uid].parent_change_set
    assert child_parent is not None
    assert child_parent.uid == parent.uid
    assert child_parent.name == "Parent"
    assert by_uid[parent.uid].parent_change_set is None


def test_hydrate_change_set_reads_skips_lookup_when_parent_in_results(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    parent_uid = uuid.uuid4()
    child_uid = uuid.uuid4()

    parent = ChangeSet(
        uid=parent_uid,
        org_uid=org_db.uid,
        state=ChangeSetState.DONE,
        name="Parent",
    )
    child = ChangeSet(
        uid=child_uid,
        org_uid=org_db.uid,
        parent_uid=parent_uid,
        state=ChangeSetState.DRAFT,
        name="Child",
    )

    # Hydration always runs exactly one query — the leaf lookup behind
    # `is_latest`. A parent lookup would be a second one, and both parents are
    # already in `change_sets`, so none should be needed. Counting rather than
    # forbidding all queries keeps this pinned to the parent lookup.
    original_execute = test_admin_session.execute
    execute_spy = MagicMock(side_effect=original_execute)
    test_admin_session.execute = execute_spy  # type: ignore[method-assign]
    try:
        hydrated = hydrate_change_set_reads(
            test_admin_session,
            org_uid=org_db.uid,
            change_sets=[child, parent],
        )
    finally:
        test_admin_session.execute = original_execute  # type: ignore[method-assign]

    assert (
        execute_spy.call_count == 1
    ), "No parent lookup query should run when parent is already in results"

    by_uid = {change_set.uid: change_set for change_set in hydrated}
    child_parent = by_uid[child_uid].parent_change_set
    assert child_parent is not None
    assert child_parent.uid == parent_uid
    assert child_parent.name == "Parent"


def test_hydrate_change_set_reads_sets_coverage(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    partial = ChangeSet(
        org_uid=org_db.uid,
        state=ChangeSetState.DONE,
        datashape={
            "commodityLocationCount": 4,
            "commodityLocationsWithSpendCount": 1,
            "fullCommoditySpendCoverage": False,
        },
    )
    without_datashape = ChangeSet(org_uid=org_db.uid, state=ChangeSetState.DONE)
    test_admin_session.add_all([partial, without_datashape])
    test_admin_session.flush()

    hydrated = hydrate_change_set_reads(
        test_admin_session,
        org_uid=org_db.uid,
        change_sets=[partial, without_datashape],
    )

    by_uid = {change_set.uid: change_set for change_set in hydrated}
    assert by_uid[partial.uid].commodity_spend_coverage == DataCoverage.PARTIAL
    assert by_uid[without_datashape.uid].commodity_spend_coverage is None


# ---------------------------------------------------------------------------
def test_get_change_summary_raises_when_change_set_does_not_exist(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_db: OrganisationDB,
):
    with pytest.raises(ChangeSetNotFoundError, match="not found"):
        get_change_summary(
            test_admin_session,
            org_uid=org_db.uid,
            change_set_uid=uuid.uuid4(),
        )


# ---------------------------------------------------------------------------
# patch_change_set
# ---------------------------------------------------------------------------


def _get_persisted_change_set(
    session: SafeSession, change_set_uid: uuid.UUID
) -> ChangeSet:
    session.rollback()
    return session.execute(
        select(ChangeSet).where(ChangeSet.uid == change_set_uid)
    ).scalar_one()


def test_patch_change_set_updates_name(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE, name="Old Name")
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        name="New Name",
    )
    persisted = _get_persisted_change_set(test_admin_session, cs.uid)

    assert result.name == "New Name"
    assert result.state == ChangeSetState.DONE
    assert persisted.name == "New Name"
    assert persisted.state == ChangeSetState.DONE


def test_patch_change_set_updates_description(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(
        org_uid=org_uid,
        state=ChangeSetState.DONE,
        description="Old description",
    )
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        description="New description",
    )
    persisted = _get_persisted_change_set(test_admin_session, cs.uid)

    assert result.description == "New description"
    assert result.state == ChangeSetState.DONE
    assert persisted.description == "New description"
    assert persisted.state == ChangeSetState.DONE


def test_patch_change_set_updates_name_and_description(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE)
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        name="My Set",
        description="My description",
    )
    persisted = _get_persisted_change_set(test_admin_session, cs.uid)

    assert result.name == "My Set"
    assert result.description == "My description"
    assert result.state == ChangeSetState.DONE
    assert persisted.name == "My Set"
    assert persisted.description == "My description"
    assert persisted.state == ChangeSetState.DONE


def test_patch_change_set_updates_name_and_state(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE)
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        name="Updated",
        new_state=ChangeSetState.PUBLISHED,
    )
    persisted = _get_persisted_change_set(test_admin_session, cs.uid)

    assert result.name == "Updated"
    assert result.state == ChangeSetState.PUBLISHED
    assert persisted.name == "Updated"
    assert persisted.state == ChangeSetState.PUBLISHED


def test_patch_change_set_updates_state_without_name_or_description(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(
        org_uid=org_uid,
        state=ChangeSetState.DONE,
        name="Keep Me",
        description="Keep this too",
    )
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        new_state=ChangeSetState.PUBLISHED,
    )
    persisted = _get_persisted_change_set(test_admin_session, cs.uid)

    assert result.state == ChangeSetState.PUBLISHED
    assert result.name == "Keep Me"
    assert result.description == "Keep this too"
    assert persisted.state == ChangeSetState.PUBLISHED
    assert persisted.name == "Keep Me"
    assert persisted.description == "Keep this too"


def test_patch_change_set_sets_published_at_when_published(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(
        org_uid=org_uid,
        state=ChangeSetState.DONE,
        unpublished_at=datetime(2026, 1, 1),
    )
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        new_state=ChangeSetState.PUBLISHED,
    )

    assert result.state == ChangeSetState.PUBLISHED
    assert result.published_at is not None
    # Republishing clears the "unpublished" signal, since it's no longer
    # accurate to describe the version as currently unpublished.
    assert result.unpublished_at is None


def test_patch_change_set_clears_published_at_when_unpublished(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(
        org_uid=org_uid,
        state=ChangeSetState.PUBLISHED,
        published_at=datetime(2026, 1, 1),
        processed_at=datetime(2026, 1, 1),
    )
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        new_state=ChangeSetState.DONE,
    )

    assert result.state == ChangeSetState.DONE
    assert result.published_at is None
    assert result.processed_at == datetime(2026, 1, 1)
    assert result.unpublished_at is not None


def test_patch_change_set_does_not_set_unpublished_at_for_unrelated_transitions(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    """Only a PUBLISHED -> DONE transition (an unpublish) should populate
    unpublished_at - not the initial DRAFT -> PROCESSING -> DONE path a
    version takes on its way to being published for the first time."""
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.PROCESSING)
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        new_state=ChangeSetState.DONE,
    )

    assert result.state == ChangeSetState.DONE
    assert result.unpublished_at is None


def test_patch_change_set_does_not_set_processed_at_when_set_to_done(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.PUBLISHED)
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        new_state=ChangeSetState.DONE,
    )

    assert result.state == ChangeSetState.DONE
    assert result.processed_at is None


def test_patch_change_set_does_not_overwrite_name_when_not_provided(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE, name="Existing")
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        description="New desc",
    )
    persisted = _get_persisted_change_set(test_admin_session, cs.uid)

    assert result.name == "Existing"
    assert result.description == "New desc"
    assert persisted.name == "Existing"
    assert persisted.description == "New desc"


def test_patch_change_set_raises_when_not_found(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    with pytest.raises(ChangeSetNotFoundError, match="not found"):
        patch_change_set(
            test_admin_session,
            org_uid=org_uid,
            change_set_uid=uuid.uuid4(),
            name="New Name",
        )


def test_patch_change_set_raises_when_wrong_org(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE)
    test_admin_session.add(cs)
    test_admin_session.flush()

    with pytest.raises(ChangeSetNotFoundError, match="not found"):
        patch_change_set(
            test_admin_session,
            org_uid=uuid.uuid4(),
            change_set_uid=cs.uid,
            name="Nope",
        )


def test_patch_change_set_raises_on_invalid_state_transition(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DRAFT)
    test_admin_session.add(cs)
    test_admin_session.flush()

    with pytest.raises(ChangeSetProcessingError, match="Cannot transition"):
        patch_change_set(
            test_admin_session,
            org_uid=org_uid,
            change_set_uid=cs.uid,
            new_state=ChangeSetState.PUBLISHED,
        )


def _record_exported_commodity_location(
    session: SafeSession,
    org_uid: uuid.UUID,
    change_set: ChangeSet,
    *,
    quantity_kilograms: float | None,
    spend: float | None,
) -> None:
    exported = ExportedCommodityLocation(
        org_uid=org_uid,
        identifier=f"C-{uuid.uuid4().hex[:8]}",
        commodity_type="crop",
        commodity_subgroup="cereals",
        commodity_code="WHEAT",
        year_purchased=2024,
        quantity_kilograms=quantity_kilograms,
        spend=spend,
    )
    session.add(exported)
    session.flush()
    session.add(
        Change(
            org_uid=org_uid,
            change_set_uid=change_set.uid,
            model_type=ExportedCommodityLocation.__tablename__,
            description="Data template uploads",
            new_uid=exported.uid,
        )
    )
    session.flush()


def test_patch_change_set_describes_exported_rows_when_set_to_processing(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DRAFT)
    test_admin_session.add(cs)
    test_admin_session.flush()
    _record_exported_commodity_location(
        test_admin_session, org_uid, cs, quantity_kilograms=1.0, spend=None
    )
    _record_exported_commodity_location(
        test_admin_session, org_uid, cs, quantity_kilograms=1.0, spend=2.0
    )

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        new_state=ChangeSetState.PROCESSING,
    )
    persisted = _get_persisted_change_set(test_admin_session, cs.uid)

    expected = "2 commodity sources. Commodity quantity: full. Commodity spend: partial"
    assert result.description == expected
    assert persisted.description == expected


def test_patch_change_set_counts_only_this_change_sets_exported_rows(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    parent = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE)
    test_admin_session.add(parent)
    test_admin_session.flush()
    _record_exported_commodity_location(
        test_admin_session, org_uid, parent, quantity_kilograms=1.0, spend=1.0
    )
    cs = ChangeSet(
        org_uid=org_uid, state=ChangeSetState.DRAFT, parent_uid=parent.uid
    )
    test_admin_session.add(cs)
    test_admin_session.flush()
    _record_exported_commodity_location(
        test_admin_session, org_uid, cs, quantity_kilograms=None, spend=None
    )

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        new_state=ChangeSetState.PROCESSING,
    )

    assert result.description == (
        "1 commodity source."
        " Commodity quantity: missing. Commodity spend: missing"
    )


def test_patch_change_set_keeps_null_description_without_exported_rows(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DRAFT)
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        new_state=ChangeSetState.PROCESSING,
    )

    assert result.description is None


def test_patch_change_set_keeps_existing_description_when_set_to_processing(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(
        org_uid=org_uid,
        state=ChangeSetState.DRAFT,
        description="Hand-written",
    )
    test_admin_session.add(cs)
    test_admin_session.flush()
    _record_exported_commodity_location(
        test_admin_session, org_uid, cs, quantity_kilograms=1.0, spend=1.0
    )

    result = patch_change_set(
        test_admin_session,
        org_uid=org_uid,
        change_set_uid=cs.uid,
        new_state=ChangeSetState.PROCESSING,
    )

    assert result.description == "Hand-written"
