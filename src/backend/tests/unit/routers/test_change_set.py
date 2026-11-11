import uuid
from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from src.backend.app.api.v1 import change_set as change_set_v1
from src.backend.app.database import Session
from src.backend.app.errors.errors import (
    ChangeSetNotFoundError,
    ChangeSetProcessingError,
)
from src.backend.app.main import app
from src.backend.app.models.change_set import ChangeSet
from src.backend.app.models.organisation import Organisation
from src.backend.app.schemas.change_set import (
    ChangeSetRead,
    ChangeSetSummary,
    UnitOfAnalysisChangeSummary,
    UnitOfAnalysisChangeSummaryBreakdown,
)
from src.backend.app.schemas.organisation import OrganisationDB
from src.backend.app.schemas.user import User
from src.backend.app.util.enums import ChangeSetState, UnitOfAnalysis
from src.backend.app.util.pagination import Paginator
from src.backend.conftest import ClientGetter


@pytest.fixture
def test_change_set() -> ChangeSet:
    cs = ChangeSet(
        uid=uuid.uuid4(),
        org_uid=uuid.uuid4(),
        parent_uid=None,
        state=ChangeSetState.DRAFT,
        name="Test Change Set",
        description="A test change set",
    )
    return cs


@pytest.fixture
def make_change_set(
    make_org_orm: Callable[..., Organisation],
    test_db_session: Session,
    test_org: OrganisationDB,
) -> Callable[..., ChangeSet]:
    """Save a change set in the client's org.

    The routes check visibility with get_visible_change_set_or_404, a real
    lookup, so a change set has to exist in the org the client sends.
    """
    make_org_orm()

    def _make(
        state: ChangeSetState = ChangeSetState.DRAFT,
        name: str = "Test Change Set",
        description: str = "A test change set",
    ) -> ChangeSet:
        cs = ChangeSet(
            org_uid=test_org.uid,
            parent_uid=None,
            state=state,
            name=name,
            description=description,
        )
        test_db_session.add(cs)
        test_db_session.commit()
        return cs

    return _make


@pytest.fixture
def saved_change_set(make_change_set: Callable[..., ChangeSet]) -> ChangeSet:
    return make_change_set()


@pytest.fixture
def org_member_user() -> User:
    """A non-admin (viewer) user of the client's org."""
    return User(
        uid="demo|member@example.com",
        email="member@example.com",
        roles=["viewer"],
        nickname="member",
    )


def test_get_change_set_by_uid(
    get_client: ClientGetter,
    saved_change_set: ChangeSet,
):
    with get_client(app) as client:
        res = client.get(
            "/api/v1/change-set/",
            params={"change_set_uid": str(saved_change_set.uid)},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["uid"] == str(saved_change_set.uid)
    assert body["state"] == "draft"
    assert body["name"] == "Test Change Set"


def test_get_change_set_default(
    get_client: ClientGetter,
    saved_change_set: ChangeSet,
    test_org: OrganisationDB,
):
    """With no change_set_uid, the org's default change set is returned."""
    org = test_org.model_copy(
        update={"default_change_set_uid": saved_change_set.uid}
    )
    with get_client(app, org=org) as client:
        res = client.get("/api/v1/change-set/")

    assert res.status_code == 200
    assert res.json()["uid"] == str(saved_change_set.uid)


def test_get_change_set_no_default_returns_404(
    get_client: ClientGetter,
    make_org_orm: Callable[..., Organisation],
):
    """A new org has no change sets, so no default either."""
    make_org_orm()
    with get_client(app) as client:
        res = client.get("/api/v1/change-set/")

    assert res.status_code == 404


def test_get_change_set_not_found(
    get_client: ClientGetter,
    make_org_orm: Callable[..., Organisation],
):
    make_org_orm()
    with get_client(app) as client:
        res = client.get(
            "/api/v1/change-set/",
            params={"change_set_uid": str(uuid.uuid4())},
        )

    assert res.status_code == 404


# ---------------------------------------------------------------------------
# get_change_sets (list endpoint)
# ---------------------------------------------------------------------------


@pytest.fixture
def test_change_set_read(test_change_set: ChangeSet) -> ChangeSetRead:
    return ChangeSetRead.model_validate(test_change_set)


def test_get_change_sets(
    get_client: ClientGetter,
    test_change_set_read: ChangeSetRead,
    monkeypatch: pytest.MonkeyPatch,
):
    with get_client(app) as client, monkeypatch.context() as _m:
        mock_get = MagicMock(
            return_value=(
                [test_change_set_read],
                MagicMock(
                    spec=Paginator,
                    next_cursor=None,
                    prev_cursor=None,
                    total_count=1,
                ),
            )
        )
        _m.setattr(change_set_v1, "get_change_sets", mock_get)

        res = client.get("/api/v1/change-sets/")

    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["uid"] == str(test_change_set_read.uid)
    assert body[0]["state"] == "draft"
    assert "natcap-next-cursor" in res.headers
    assert "natcap-total-count" in res.headers
    assert res.headers["natcap-total-count"] == "1"
    mock_get.assert_called_once()


def test_get_change_sets_empty(
    get_client: ClientGetter,
    monkeypatch: pytest.MonkeyPatch,
):
    with get_client(app) as client, monkeypatch.context() as _m:
        mock_get = MagicMock(
            return_value=(
                [],
                MagicMock(
                    spec=Paginator,
                    next_cursor=None,
                    prev_cursor=None,
                    total_count=0,
                ),
            )
        )
        _m.setattr(change_set_v1, "get_change_sets", mock_get)

        res = client.get("/api/v1/change-sets/")

    assert res.status_code == 200
    body = res.json()
    assert body == []
    assert res.headers["natcap-total-count"] == "0"
    mock_get.assert_called_once()


def test_get_change_sets_with_state_filter(
    get_client: ClientGetter,
    test_change_set_read: ChangeSetRead,
    monkeypatch: pytest.MonkeyPatch,
):
    with get_client(app) as client, monkeypatch.context() as _m:
        mock_get = MagicMock(
            return_value=(
                [test_change_set_read],
                MagicMock(
                    spec=Paginator,
                    next_cursor=None,
                    prev_cursor=None,
                    total_count=1,
                ),
            )
        )
        _m.setattr(change_set_v1, "get_change_sets", mock_get)

        res = client.get(
            "/api/v1/change-sets/",
            params={"state": "draft"},
        )

    assert res.status_code == 200
    assert len(res.json()) == 1
    # Verify state was passed through to the API function
    call_kwargs = mock_get.call_args
    assert call_kwargs.kwargs["state"] == ChangeSetState.DRAFT


# ---------------------------------------------------------------------------
def test_patch_change_set_updates_name(
    get_client: ClientGetter,
    test_change_set: ChangeSet,
    monkeypatch: pytest.MonkeyPatch,
):
    updated = ChangeSet(
        uid=test_change_set.uid,
        org_uid=test_change_set.org_uid,
        state=test_change_set.state,
        name="New Name",
        description=test_change_set.description,
    )
    with get_client(app) as client, monkeypatch.context() as _m:
        mock_patch = MagicMock(return_value=updated)
        _m.setattr(change_set_v1, "patch_change_set", mock_patch)

        res = client.patch(
            f"/api/v1/change-sets/{test_change_set.uid}/",
            json={"name": "New Name"},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "New Name"
    mock_patch.assert_called_once()
    call_kwargs = mock_patch.call_args.kwargs
    assert call_kwargs["name"] == "New Name"
    assert call_kwargs["description"] is None
    assert call_kwargs["new_state"] is None


def test_patch_change_set_updates_description(
    get_client: ClientGetter,
    test_change_set: ChangeSet,
    monkeypatch: pytest.MonkeyPatch,
):
    updated = ChangeSet(
        uid=test_change_set.uid,
        org_uid=test_change_set.org_uid,
        state=test_change_set.state,
        name=test_change_set.name,
        description="New desc",
    )
    with get_client(app) as client, monkeypatch.context() as _m:
        mock_patch = MagicMock(return_value=updated)
        _m.setattr(change_set_v1, "patch_change_set", mock_patch)

        res = client.patch(
            f"/api/v1/change-sets/{test_change_set.uid}/",
            json={"description": "New desc"},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["description"] == "New desc"
    mock_patch.assert_called_once()


def test_patch_change_set_updates_name_description_and_state(
    get_client: ClientGetter,
    test_change_set: ChangeSet,
    monkeypatch: pytest.MonkeyPatch,
):
    updated = ChangeSet(
        uid=test_change_set.uid,
        org_uid=test_change_set.org_uid,
        state=ChangeSetState.PUBLISHED,
        name="Final",
        description="Done",
    )
    with get_client(app) as client, monkeypatch.context() as _m:
        mock_patch = MagicMock(return_value=updated)
        _m.setattr(change_set_v1, "patch_change_set", mock_patch)

        res = client.patch(
            f"/api/v1/change-sets/{test_change_set.uid}/",
            json={"name": "Final", "description": "Done", "state": "published"},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Final"
    assert body["description"] == "Done"
    assert body["state"] == "published"
    call_kwargs = mock_patch.call_args.kwargs
    assert call_kwargs["name"] == "Final"
    assert call_kwargs["description"] == "Done"
    assert call_kwargs["new_state"] == ChangeSetState.PUBLISHED


def test_patch_change_set_viewer_cannot_update_name(
    get_client: ClientGetter,
    test_change_set: ChangeSet,
    test_viewer_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    """Viewers hold no update:change_set:basic, so even a rename is refused."""
    with (
        get_client(app, user=test_viewer_user) as client,
        monkeypatch.context() as _m,
    ):
        mock_patch = MagicMock()
        _m.setattr(change_set_v1, "patch_change_set", mock_patch)

        res = client.patch(
            f"/api/v1/change-sets/{test_change_set.uid}/",
            json={"name": "Nope"},
        )

    assert res.status_code == 403
    mock_patch.assert_not_called()


def test_patch_change_set_state_requires_publish_permission(
    get_client: ClientGetter,
    test_change_set: ChangeSet,
    test_viewer_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    """Viewers cannot transition change set state (requires
    update:change_set:publish)."""
    with (
        get_client(app, user=test_viewer_user) as client,
        monkeypatch.context() as _m,
    ):
        mock_patch = MagicMock()
        _m.setattr(change_set_v1, "patch_change_set", mock_patch)

        res = client.patch(
            f"/api/v1/change-sets/{test_change_set.uid}/",
            json={"state": "published"},
        )

    assert res.status_code == 403
    mock_patch.assert_not_called()


def test_get_change_set_non_admin_can_see_draft(
    get_client: ClientGetter,
    saved_change_set: ChangeSet,
    org_member_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    """Non-admin users can see draft change sets in their org."""
    with (
        get_client(app, user=org_member_user) as client,
        monkeypatch.context() as _m,
    ):
        res = client.get(
            "/api/v1/change-set/",
            params={"change_set_uid": str(saved_change_set.uid)},
        )

    assert res.status_code == 200
    assert res.json()["state"] == "draft"


def test_get_change_set_non_admin_can_see_published(
    get_client: ClientGetter,
    make_change_set: Callable[..., ChangeSet],
    org_member_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    """Non-admin users can see published change sets."""
    published_cs = make_change_set(
        state=ChangeSetState.PUBLISHED,
        name="Published CS",
        description="A published change set",
    )
    with (
        get_client(app, user=org_member_user) as client,
        monkeypatch.context() as _m,
    ):
        res = client.get(
            "/api/v1/change-set/",
            params={"change_set_uid": str(published_cs.uid)},
        )

    assert res.status_code == 200
    assert res.json()["state"] == "published"


def test_get_change_set_non_admin_cannot_see_done(
    get_client: ClientGetter,
    make_change_set: Callable[..., ChangeSet],
    org_member_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    """Non-admin users cannot see done change sets."""
    done_cs = make_change_set(
        state=ChangeSetState.DONE,
        name="Done CS",
        description="A done change set",
    )
    with (
        get_client(app, user=org_member_user) as client,
        monkeypatch.context() as _m,
    ):
        res = client.get(
            "/api/v1/change-set/",
            params={"change_set_uid": str(done_cs.uid)},
        )

    assert res.status_code == 404


def test_get_change_sets_non_admin_sees_only_published(
    get_client: ClientGetter,
    test_change_set_read: ChangeSetRead,
    test_viewer_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    """Non-admin list endpoint limits visibility to draft and published."""
    with (
        get_client(app, user=test_viewer_user) as client,
        monkeypatch.context() as _m,
    ):
        mock_get = MagicMock(
            return_value=(
                [],
                MagicMock(
                    spec=Paginator,
                    next_cursor=None,
                    prev_cursor=None,
                    total_count=0,
                ),
            )
        )
        _m.setattr(change_set_v1, "get_change_sets", mock_get)

        res = client.get(
            "/api/v1/change-sets/",
            params={"state": "draft"},
        )

    assert res.status_code == 200
    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs["state"] == ChangeSetState.DRAFT
    assert call_kwargs["visible_states"] == {
        ChangeSetState.DRAFT,
        ChangeSetState.PUBLISHED,
    }


def test_patch_change_set_invalid_transition_returns_400(
    get_client: ClientGetter,
    test_change_set: ChangeSet,
    monkeypatch: pytest.MonkeyPatch,
):
    with get_client(app) as client, monkeypatch.context() as _m:
        mock_patch = MagicMock(
            side_effect=ChangeSetProcessingError("Cannot transition change set")
        )
        _m.setattr(change_set_v1, "patch_change_set", mock_patch)

        res = client.patch(
            f"/api/v1/change-sets/{test_change_set.uid}/",
            json={"state": "published"},
        )

    assert res.status_code == 409
    mock_patch.assert_called_once()


def test_patch_change_set_empty_body_succeeds(
    get_client: ClientGetter,
    test_change_set: ChangeSet,
    monkeypatch: pytest.MonkeyPatch,
):
    """An empty body is valid — all fields are optional."""
    with get_client(app) as client, monkeypatch.context() as _m:
        mock_patch = MagicMock(return_value=test_change_set)
        _m.setattr(change_set_v1, "patch_change_set", mock_patch)

        res = client.patch(
            f"/api/v1/change-sets/{test_change_set.uid}/",
            json={},
        )

    assert res.status_code == 200
    mock_patch.assert_called_once()
    call_kwargs = mock_patch.call_args.kwargs
    assert call_kwargs["name"] is None
    assert call_kwargs["description"] is None
    assert call_kwargs["new_state"] is None


def test_get_change_summary(
    get_client: ClientGetter,
    saved_change_set: ChangeSet,
    monkeypatch: pytest.MonkeyPatch,
):
    change_summary = ChangeSetSummary(
        org_uid=saved_change_set.org_uid,
        change_set_uid=saved_change_set.uid,
        state=saved_change_set.state,
        name=saved_change_set.name,
        description=saved_change_set.description,
        unit_of_analysis_summaries={},
    )

    with get_client(app) as client, monkeypatch.context() as _m:
        mock_get = MagicMock(return_value=change_summary)
        _m.setattr(change_set_v1, "get_change_summary", mock_get)

        res = client.get(
            f"/api/v1/change-sets/{saved_change_set.uid}/summary/",
        )

    assert res.status_code == 200
    body = res.json()
    assert body["changeSetUid"] == str(saved_change_set.uid)
    assert body["state"] == "draft"
    assert body["unitOfAnalysisSummaries"] == {}
    mock_get.assert_called_once()


def test_get_change_summary_handles_commodity_source_without_region(
    get_client: ClientGetter,
    saved_change_set: ChangeSet,
    monkeypatch: pytest.MonkeyPatch,
):
    change_summary = ChangeSetSummary(
        org_uid=saved_change_set.org_uid,
        change_set_uid=saved_change_set.uid,
        state=saved_change_set.state,
        name=saved_change_set.name,
        description=saved_change_set.description,
        unit_of_analysis_summaries={
            UnitOfAnalysis.COMMODITY_SOURCE: UnitOfAnalysisChangeSummaryBreakdown(
                regions=[
                    UnitOfAnalysisChangeSummary(value=1.0, text="unknown")
                ],
                commodities=[
                    UnitOfAnalysisChangeSummary(value=1.0, text="commodity")
                ],
            )
        },
    )

    with get_client(app) as client, monkeypatch.context() as _m:
        mock_get = MagicMock(return_value=change_summary)
        _m.setattr(change_set_v1, "get_change_summary", mock_get)

        res = client.get(
            f"/api/v1/change-sets/{saved_change_set.uid}/summary/",
        )

    assert res.status_code == 200
    body = res.json()
    commodity_source_summaries = body["unitOfAnalysisSummaries"][
        "commodity_source"
    ]["regions"]
    assert any(item["text"] == "unknown" for item in commodity_source_summaries)
    assert all(
        isinstance(item["text"], str) for item in commodity_source_summaries
    )
    mock_get.assert_called_once()


def test_get_change_summary_not_found(
    get_client: ClientGetter,
    saved_change_set: ChangeSet,
    monkeypatch: pytest.MonkeyPatch,
):
    with get_client(app) as client, monkeypatch.context() as _m:
        mock_get = MagicMock(
            side_effect=ChangeSetNotFoundError(
                f"Change set {saved_change_set.uid} not found"
            )
        )
        _m.setattr(change_set_v1, "get_change_summary", mock_get)

        res = client.get(
            f"/api/v1/change-sets/{saved_change_set.uid}/summary/",
        )

    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Sub-resource visibility: non-admin users can see draft and published change
# sets in their org via sub-resource endpoints.
# ---------------------------------------------------------------------------


def test_get_change_summary_non_admin_can_see_draft(
    get_client: ClientGetter,
    saved_change_set: ChangeSet,
    org_member_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    """Non-admin users can access summary for a draft change set."""
    with (
        get_client(app, user=org_member_user) as client,
        monkeypatch.context() as _m,
    ):
        mock_get_summary = MagicMock(
            return_value=ChangeSetSummary(
                org_uid=saved_change_set.org_uid,
                change_set_uid=saved_change_set.uid,
                state=saved_change_set.state,
                name=saved_change_set.name,
                description=saved_change_set.description,
                unit_of_analysis_summaries={},
            )
        )
        _m.setattr(change_set_v1, "get_change_summary", mock_get_summary)

        res = client.get(
            f"/api/v1/change-sets/{saved_change_set.uid}/summary/",
        )

    assert res.status_code == 200
    mock_get_summary.assert_called_once()


def test_get_change_summary_non_admin_can_see_published(
    get_client: ClientGetter,
    make_change_set: Callable[..., ChangeSet],
    org_member_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    """Non-admin users can access summary for a published change set."""
    published_cs = make_change_set(
        state=ChangeSetState.PUBLISHED,
        name="Published CS",
        description="desc",
    )
    summary = ChangeSetSummary(
        org_uid=published_cs.org_uid,
        change_set_uid=published_cs.uid,
        state=published_cs.state,
        name=published_cs.name,
        description=published_cs.description,
        unit_of_analysis_summaries={},
    )
    with (
        get_client(app, user=org_member_user) as client,
        monkeypatch.context() as _m,
    ):
        _m.setattr(
            change_set_v1,
            "get_change_summary",
            MagicMock(return_value=summary),
        )

        res = client.get(
            f"/api/v1/change-sets/{published_cs.uid}/summary/",
        )

    assert res.status_code == 200
