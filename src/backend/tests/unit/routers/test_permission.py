import uuid

from src.backend.app.main import app
from src.backend.app.schemas.user import User
from src.backend.conftest import ClientGetter


def test_root_object_permission_set_has_no_root_actions(
    get_client: ClientGetter,
):
    with get_client(app) as client:
        res = client.get("/api/v1/object-permission-set/root/")
    assert res.status_code == 200
    assert res.json() == {"object": "root", "roles": [], "scopes": []}


def test_admin_change_set_permission_set(
    get_client: ClientGetter,
    test_user: User,
):
    uid = uuid.uuid4()
    with get_client(app, user=test_user) as client:
        res = client.get(f"/api/v1/object-permission-set/change_set/{uid}/")
    assert res.status_code == 200
    assert res.json() == {
        "object": f"change_set:{uid}",
        "roles": [],
        "scopes": [
            "read:change_set:all",
            "read:change_set:basic",
            "update:change_set:basic",
            "update:change_set:publish",
        ],
    }


def test_viewer_change_set_permission_set(
    get_client: ClientGetter,
    test_viewer_user: User,
):
    uid = uuid.uuid4()
    with get_client(app, user=test_viewer_user) as client:
        res = client.get(f"/api/v1/object-permission-set/change_set/{uid}/")
    assert res.status_code == 200
    assert res.json()["scopes"] == ["read:change_set:basic"]


def test_org_permission_set_for_every_role(
    get_client: ClientGetter,
    test_user: User,
    test_viewer_user: User,
):
    uid = uuid.uuid4()
    for user in (test_user, test_viewer_user):
        with get_client(app, user=user) as client:
            res = client.get(f"/api/v1/object-permission-set/org/{uid}/")
        assert res.status_code == 200
        assert res.json()["scopes"] == ["read:org:basic"]


def test_unknown_object_has_no_actions(get_client: ClientGetter):
    uid = uuid.uuid4()
    with get_client(app) as client:
        res = client.get(f"/api/v1/object-permission-set/export/{uid}/")
    assert res.status_code == 200
    assert res.json()["scopes"] == []


def test_object_uid_must_be_a_uuid(get_client: ClientGetter):
    with get_client(app) as client:
        res = client.get("/api/v1/object-permission-set/org/not-a-uuid/")
    assert res.status_code == 422
