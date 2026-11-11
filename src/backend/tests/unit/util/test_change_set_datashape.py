import uuid
from collections.abc import Callable

import pytest
from pydantic import ValidationError
from src.backend.app.access import SafeSession
from src.backend.app.models.change_set import Change, ChangeSet
from src.backend.app.models.commodity_location_entity import (
    CommodityLocationEntity,
)
from src.backend.app.models.export.exported_commodity_location import (
    ExportedCommodityLocation,
)
from src.backend.app.models.organisation import Organisation
from src.backend.app.schemas.change_set import (
    ChangeSetDataShape,
    commodity_spend_coverage,
)
from src.backend.app.util.change_set import (
    compute_change_set_datashape,
    create_change_set,
    refresh_change_set_datashape,
)
from src.backend.app.util.enums import ChangeSetState, DataCoverage


@pytest.fixture
def org_uid(
    make_org_orm: Callable[..., Organisation],
) -> uuid.UUID:
    return make_org_orm().uid


def _make_change_set(
    session: SafeSession,
    org_uid: uuid.UUID,
    state: ChangeSetState,
    parent: ChangeSet | None = None,
) -> ChangeSet:
    change_set = ChangeSet(
        org_uid=org_uid,
        state=state,
        parent_uid=parent.uid if parent else None,
    )
    session.add(change_set)
    session.flush()
    return change_set


def _record(
    session: SafeSession,
    change_set: ChangeSet,
    row: CommodityLocationEntity | ExportedCommodityLocation,
    *,
    tombstone: bool = False,
) -> None:
    session.add(
        Change(
            org_uid=change_set.org_uid,
            change_set_uid=change_set.uid,
            model_type=type(row).__tablename__,
            new_uid=None if tombstone else row.uid,
            previous_uid=row.uid if tombstone else None,
            description="test",
        )
    )
    session.flush()


def _add_commodity_location_row(
    session: SafeSession,
    change_set: ChangeSet,
    entity: CommodityLocationEntity,
    spend: float | None,
) -> None:
    row = ExportedCommodityLocation(
        org_uid=change_set.org_uid,
        entity_uid=entity.uid,
        identifier=entity.identifier,
        commodity_type="Crop",
        commodity_subgroup="Cereals",
        commodity_code="WHEAT",
        year_purchased=2024,
        spend=spend,
    )
    session.add(row)
    session.flush()
    _record(session, change_set, row)


def _add_commodity_location(
    session: SafeSession,
    change_set: ChangeSet,
    identifier: str,
    spend: float | None,
) -> CommodityLocationEntity:
    entity = CommodityLocationEntity(
        org_uid=change_set.org_uid,
        identifier=identifier,
        commodity_type="Crop",
        commodity_subgroup="Cereals",
        commodity_code="WHEAT",
        year_purchased=2024,
        normalised_key=identifier,
    )
    session.add(entity)
    session.flush()
    _record(session, change_set, entity)
    _add_commodity_location_row(session, change_set, entity, spend)
    return entity


# ---------------------------------------------------------------------------
# ChangeSetDataShape validation
# ---------------------------------------------------------------------------


def test_datashape_serialises_with_camel_case_keys():
    shape = ChangeSetDataShape(
        commodity_location_count=3,
        commodity_locations_with_spend_count=1,
        full_commodity_spend_coverage=False,
    )

    assert shape.model_dump(by_alias=True) == {
        "commodityLocationCount": 3,
        "commodityLocationsWithSpendCount": 1,
        "fullCommoditySpendCoverage": False,
    }


@pytest.mark.parametrize(
    "overrides",
    [
        # More commodity locations with spend than commodity locations.
        {"commodity_locations_with_spend_count": 4},
        # A flag that disagrees with its counts.
        {"full_commodity_spend_coverage": True},
        # Full coverage of nothing.
        {
            "commodity_location_count": 0,
            "commodity_locations_with_spend_count": 0,
            "full_commodity_spend_coverage": True,
        },
        # A negative count.
        {"commodity_location_count": -1},
    ],
)
def test_datashape_rejects_inconsistent_values(overrides: dict[str, object]):
    values: dict[str, object] = {
        "commodity_location_count": 3,
        "commodity_locations_with_spend_count": 1,
        "full_commodity_spend_coverage": False,
    }

    with pytest.raises(ValidationError):
        ChangeSetDataShape.model_validate({**values, **overrides})


@pytest.mark.parametrize(
    ("commodity_location_count", "with_spend_count", "expected"),
    [
        (3, 3, DataCoverage.FULL),
        (3, 1, DataCoverage.PARTIAL),
        (3, 0, DataCoverage.NONE),
        # No commodity locations: nothing to cover, so no spend.
        (0, 0, DataCoverage.NONE),
    ],
)
def test_commodity_spend_coverage(
    commodity_location_count: int,
    with_spend_count: int,
    expected: DataCoverage,
):
    shape = ChangeSetDataShape(
        commodity_location_count=commodity_location_count,
        commodity_locations_with_spend_count=with_spend_count,
        full_commodity_spend_coverage=commodity_location_count > 0
        and with_spend_count == commodity_location_count,
    )

    assert commodity_spend_coverage(shape) == expected


# ---------------------------------------------------------------------------
# compute_change_set_datashape
# ---------------------------------------------------------------------------


def test_compute_empty_change_set_has_zero_counts_and_no_coverage(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    draft = _make_change_set(test_admin_session, org_uid, ChangeSetState.DRAFT)

    shape = compute_change_set_datashape(test_admin_session, org_uid, draft.uid)

    assert shape == ChangeSetDataShape(
        commodity_location_count=0,
        commodity_locations_with_spend_count=0,
        full_commodity_spend_coverage=False,
    )


def test_compute_counts_rows_current_as_of_the_change_set(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    session = test_admin_session
    version = _make_change_set(session, org_uid, ChangeSetState.DONE)
    _add_commodity_location(session, version, "kept", spend=10.0)
    deleted = _add_commodity_location(session, version, "deleted", spend=20.0)
    spend_removed = _add_commodity_location(
        session, version, "spend-removed", spend=30.0
    )
    _add_commodity_location(session, version, "with-zero-spend", spend=0.0)
    _add_commodity_location(session, version, "without-spend", spend=None)

    draft = _make_change_set(
        session, org_uid, ChangeSetState.DRAFT, parent=version
    )
    _record(session, draft, deleted, tombstone=True)
    _add_commodity_location_row(session, draft, spend_removed, spend=None)

    shape = compute_change_set_datashape(session, org_uid, draft.uid)

    # "deleted" is gone, "spend-removed" reads its draft row, and a spend of
    # 0 is a provided spend.
    assert shape == ChangeSetDataShape(
        commodity_location_count=4,
        commodity_locations_with_spend_count=2,
        full_commodity_spend_coverage=False,
    )


def test_compute_full_coverage(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    session = test_admin_session
    draft = _make_change_set(session, org_uid, ChangeSetState.DRAFT)
    _add_commodity_location(session, draft, "a", spend=5.0)
    _add_commodity_location(session, draft, "b", spend=0.0)

    shape = compute_change_set_datashape(session, org_uid, draft.uid)

    assert shape.full_commodity_spend_coverage is True


# ---------------------------------------------------------------------------
# refresh_change_set_datashape / create_change_set
# ---------------------------------------------------------------------------


def test_refresh_stores_datashape_on_draft(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    session = test_admin_session
    draft = _make_change_set(session, org_uid, ChangeSetState.DRAFT)
    _add_commodity_location(session, draft, "c", spend=5.0)

    refresh_change_set_datashape(session, draft)

    assert draft.datashape == {
        "commodityLocationCount": 1,
        "commodityLocationsWithSpendCount": 1,
        "fullCommoditySpendCoverage": True,
    }


@pytest.mark.parametrize(
    "state",
    [state for state in ChangeSetState if state != ChangeSetState.DRAFT],
)
def test_refresh_rejects_non_draft(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    state: ChangeSetState,
):
    change_set = _make_change_set(test_admin_session, org_uid, state)

    with pytest.raises(ValueError, match="expected draft"):
        refresh_change_set_datashape(test_admin_session, change_set)

    assert change_set.datashape is None


def test_create_change_set_stores_inherited_datashape(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    session = test_admin_session
    version = _make_change_set(session, org_uid, ChangeSetState.DONE)
    _add_commodity_location(session, version, "c", spend=None)

    draft = create_change_set(session, org_uid)

    assert draft.parent_uid == version.uid
    assert draft.datashape == {
        "commodityLocationCount": 1,
        "commodityLocationsWithSpendCount": 0,
        "fullCommoditySpendCoverage": False,
    }
