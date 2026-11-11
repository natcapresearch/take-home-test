import uuid

from fastapi import status
from src.backend.app.main import app
from src.backend.app.middleware import ORG_UID_HEADER
from src.backend.app.schemas.user import User
from src.backend.conftest import ClientGetter


def test_no_header_allowed(
    set_up_test_db: None,
    get_client: ClientGetter,
):
    header: dict[str, str] = {}
    with get_client(app) as client:
        res = client.get("/health", headers=header)
    assert res.status_code == status.HTTP_200_OK


def test_empty_org_header_not_allowed(
    set_up_test_db: None,
    get_client: ClientGetter,
):
    header = {
        ORG_UID_HEADER: "",
    }
    with get_client(app) as client:
        res = client.get("/health", headers=header)
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_invalid_org_uuid_not_allowed(
    set_up_test_db: None,
    get_client: ClientGetter,
):
    header = {
        ORG_UID_HEADER: "not-a-uuid",
    }
    with get_client(app) as client:
        res = client.get("/health", headers=header)
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_org_uuidv1_not_allowed(
    set_up_test_db: None,
    get_client: ClientGetter,
):
    header = {
        ORG_UID_HEADER: str(uuid.uuid1()),
    }
    with get_client(app) as client:
        res = client.get("/health", headers=header)
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_valid_org_uuid_passes_through(
    set_up_test_db: None,
    get_client: ClientGetter,
):
    header = {
        ORG_UID_HEADER: str(uuid.uuid4()),
    }
    with get_client(app) as client:
        res = client.get("/health", headers=header)
    assert res.status_code == status.HTTP_200_OK


def test_demo_user_middleware_sets_the_configured_user(
    set_up_test_db: None,
    get_client: ClientGetter,
):
    """With no dependency override, the user on the request is the one the
    DEMO_USER_* settings describe (which the test client points at `user`)."""
    from src.backend.app import deps

    viewer = User(
        uid="demo|someone@example.com",
        email="someone@example.com",
        nickname="Someone",
        roles=["viewer"],
    )
    with get_client(app, user=viewer) as client:
        app.dependency_overrides.pop(deps.current_user)
        res = client.get("/api/v1/users/current/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json() == {
        "uid": "demo|someone@example.com",
        "email": "someone@example.com",
        "nickname": "Someone",
    }
