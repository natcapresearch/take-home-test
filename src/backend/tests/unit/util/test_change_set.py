import uuid
from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from src.backend.app.access import SafeSession
from src.backend.app.errors.errors import ChangeSetNotFoundError
from src.backend.app.models.change_set import ChangeSet
from src.backend.app.models.commodity_location_entity import (
    CommodityLocationEntity,
)
from src.backend.app.models.organisation import Organisation
from src.backend.app.schemas.organisation import OrganisationDB
from src.backend.app.util.change_set import (
    create_change,
    create_change_set,
    get_latest_change_set,
    get_visible_change_set_or_404,
)
from src.backend.app.util.enums import ChangeSetState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org_uid(
    make_org_orm: Callable[..., Organisation],
) -> uuid.UUID:
    org = make_org_orm()
    return org.uid


# ---------------------------------------------------------------------------
# get_visible_change_set_or_404
# ---------------------------------------------------------------------------


def _access(*roles: str) -> MagicMock:
    """Visibility is gated on `read:change_set:all`, which admins hold."""
    access = MagicMock()
    access.user.roles = list(roles)
    access.check.return_value = "admin" in roles
    return access


def _not_found_message(
    safe_session: SafeSession,
    access: MagicMock,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
) -> str:
    with pytest.raises(ChangeSetNotFoundError) as exc_info:
        get_visible_change_set_or_404(
            safe_session, access, org_uid, change_set_uid
        )
    return str(exc_info.value)


@pytest.mark.parametrize("state", list(ChangeSetState))
def test_get_visible_change_set_or_404_returns_any_state_for_admin(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    state: ChangeSetState,
):
    cs = ChangeSet(org_uid=org_uid, state=state)
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = get_visible_change_set_or_404(
        test_admin_session, _access("admin"), org_uid, cs.uid
    )

    assert isinstance(result, ChangeSet)
    assert result.uid == cs.uid


@pytest.mark.parametrize(
    "state", [ChangeSetState.DRAFT, ChangeSetState.PUBLISHED]
)
def test_get_visible_change_set_or_404_returns_visible_state_for_non_admin(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    state: ChangeSetState,
):
    cs = ChangeSet(org_uid=org_uid, state=state)
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = get_visible_change_set_or_404(
        test_admin_session, _access("viewer"), org_uid, cs.uid
    )

    assert result.uid == cs.uid


@pytest.mark.parametrize(
    "state", [ChangeSetState.PROCESSING, ChangeSetState.DONE]
)
def test_get_visible_change_set_or_404_raises_for_hidden_state_for_non_admin(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    state: ChangeSetState,
):
    cs = ChangeSet(org_uid=org_uid, state=state)
    test_admin_session.add(cs)
    test_admin_session.flush()

    with pytest.raises(ChangeSetNotFoundError):
        get_visible_change_set_or_404(
            test_admin_session, _access("viewer"), org_uid, cs.uid
        )


def test_get_visible_change_set_or_404_raises_when_uid_not_found(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    with pytest.raises(ChangeSetNotFoundError):
        get_visible_change_set_or_404(
            test_admin_session, _access("admin"), org_uid, uuid.uuid4()
        )


def test_get_visible_change_set_or_404_raises_for_other_org_even_for_admin(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_org_orm: Callable[..., Organisation],
):
    other_org = OrganisationDB(
        uid=uuid.uuid4(),
        name="Other Org",
    )
    make_org_orm(other_org)
    cs = ChangeSet(org_uid=other_org.uid, state=ChangeSetState.PUBLISHED)
    test_admin_session.add(cs)
    test_admin_session.flush()

    with pytest.raises(ChangeSetNotFoundError):
        get_visible_change_set_or_404(
            test_admin_session, _access("admin"), org_uid, cs.uid
        )


def test_get_visible_change_set_or_404_failures_are_indistinguishable(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_org_orm: Callable[..., Organisation],
):
    """Missing, other-org and hidden must not leak which one it was."""
    other_org = OrganisationDB(
        uid=uuid.uuid4(),
        name="Other Org",
    )
    make_org_orm(other_org)
    hidden = ChangeSet(org_uid=org_uid, state=ChangeSetState.PROCESSING)
    other = ChangeSet(org_uid=other_org.uid, state=ChangeSetState.PUBLISHED)
    test_admin_session.add_all([hidden, other])
    test_admin_session.flush()

    non_admin = _access("viewer")
    messages = {
        _not_found_message(test_admin_session, non_admin, org_uid, uid)
        for uid in (uuid.uuid4(), other.uid, hidden.uid)
    }

    assert messages == {"Change set not found."}


# ---------------------------------------------------------------------------
# get_latest_change_set
# ---------------------------------------------------------------------------


def test_get_latest_change_set_returns_none_when_no_change_sets(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    result = get_latest_change_set(test_admin_session, org_uid)
    assert result is None


def test_get_latest_change_set_returns_single_change_set(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE)
    test_admin_session.add(cs)
    test_admin_session.flush()

    result = get_latest_change_set(test_admin_session, org_uid)
    assert result is not None
    assert result.uid == cs.uid


def test_get_latest_change_set_returns_leaf_when_chain_exists(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    first = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE)
    test_admin_session.add(first)
    test_admin_session.flush()

    second = ChangeSet(
        org_uid=org_uid, parent_uid=first.uid, state=ChangeSetState.DONE
    )
    test_admin_session.add(second)
    test_admin_session.flush()

    result = get_latest_change_set(test_admin_session, org_uid)
    assert result is not None
    assert result.uid == second.uid


def test_get_latest_change_set_raises_when_multiple_leaves(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs1 = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE)
    cs2 = ChangeSet(org_uid=org_uid, state=ChangeSetState.DRAFT)
    test_admin_session.add_all([cs1, cs2])
    test_admin_session.flush()

    with pytest.raises(ValueError, match="Multiple leaf change sets"):
        get_latest_change_set(test_admin_session, org_uid)


# ---------------------------------------------------------------------------
# create_change_set
# ---------------------------------------------------------------------------


def test_create_change_set_with_no_parent_when_no_existing(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    result = create_change_set(test_admin_session, org_uid)
    test_admin_session.flush()

    assert result.org_uid == org_uid
    assert result.parent_uid is None
    assert result.state == ChangeSetState.DRAFT


def test_create_change_set_with_parent_when_single_existing(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    existing = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE)
    test_admin_session.add(existing)
    test_admin_session.flush()

    result = create_change_set(test_admin_session, org_uid)
    test_admin_session.flush()

    assert result.parent_uid == existing.uid
    assert result.state == ChangeSetState.DRAFT


def test_create_change_set_with_leaf_parent_in_chain(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    first = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE)
    test_admin_session.add(first)
    test_admin_session.flush()

    second = ChangeSet(
        org_uid=org_uid, parent_uid=first.uid, state=ChangeSetState.DONE
    )
    test_admin_session.add(second)
    test_admin_session.flush()

    result = create_change_set(test_admin_session, org_uid)
    test_admin_session.flush()

    assert result.parent_uid == second.uid
    assert result.state == ChangeSetState.DRAFT


# ---------------------------------------------------------------------------
# create_change
# ---------------------------------------------------------------------------


def test_create_change_adds_change_to_draft_change_set(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DRAFT)
    test_admin_session.add(cs)
    test_admin_session.flush()

    change = create_change(
        test_admin_session,
        org_uid=org_uid,
        change_set=cs,
        model_type=CommodityLocationEntity,
        description="Added site",
        new_uid=uuid.uuid4(),
    )
    test_admin_session.flush()

    assert change.change_set_uid == cs.uid
    assert change.org_uid == org_uid
    assert change.model_type == "commodity_location_entity"
    assert change.description == "Added site"
    assert change.new_uid is not None
    assert change.previous_uid is None


def test_create_change_with_previous_uid(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DRAFT)
    test_admin_session.add(cs)
    test_admin_session.flush()

    prev = uuid.uuid4()
    change = create_change(
        test_admin_session,
        org_uid=org_uid,
        change_set=cs,
        model_type=CommodityLocationEntity,
        description="Removed site",
        previous_uid=prev,
    )
    test_admin_session.flush()

    assert change.change_set_uid == cs.uid
    assert change.previous_uid == prev
    assert change.new_uid is None


def test_create_change_with_both_uids_for_update(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DRAFT)
    test_admin_session.add(cs)
    test_admin_session.flush()

    prev = uuid.uuid4()
    new = uuid.uuid4()
    change = create_change(
        test_admin_session,
        org_uid=org_uid,
        change_set=cs,
        model_type=CommodityLocationEntity,
        description="Updated site",
        new_uid=new,
        previous_uid=prev,
    )
    test_admin_session.flush()

    assert change.new_uid == new
    assert change.previous_uid == prev


def test_create_change_raises_when_change_set_is_completed(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DONE)
    test_admin_session.add(cs)
    test_admin_session.flush()

    with pytest.raises(ValueError, match="Cannot add change"):
        create_change(
            test_admin_session,
            org_uid=org_uid,
            change_set=cs,
            model_type=CommodityLocationEntity,
            description="Added site",
            new_uid=uuid.uuid4(),
        )


def test_create_change_raises_when_change_set_is_published(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.PUBLISHED)
    test_admin_session.add(cs)
    test_admin_session.flush()

    with pytest.raises(ValueError, match="Cannot add change"):
        create_change(
            test_admin_session,
            org_uid=org_uid,
            change_set=cs,
            model_type=CommodityLocationEntity,
            description="Added site",
            new_uid=uuid.uuid4(),
        )


def test_create_change_raises_when_change_set_is_processing(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.PROCESSING)
    test_admin_session.add(cs)
    test_admin_session.flush()

    with pytest.raises(ValueError, match="Cannot add change"):
        create_change(
            test_admin_session,
            org_uid=org_uid,
            change_set=cs,
            model_type=CommodityLocationEntity,
            description="Added site",
            new_uid=uuid.uuid4(),
        )


def test_create_change_raises_when_org_uid_does_not_match(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
):
    cs = ChangeSet(org_uid=org_uid, state=ChangeSetState.DRAFT)
    test_admin_session.add(cs)
    test_admin_session.flush()

    other_org_uid = uuid.uuid4()

    with pytest.raises(ValueError, match="does not belong to organisation"):
        create_change(
            test_admin_session,
            org_uid=other_org_uid,
            change_set=cs,
            model_type=CommodityLocationEntity,
            description="Added site",
            new_uid=uuid.uuid4(),
        )
