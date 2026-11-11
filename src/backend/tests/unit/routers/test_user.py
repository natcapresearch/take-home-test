from src.backend.app import deps
from src.backend.app.main import app
from src.backend.app.schemas.user import User
from src.backend.conftest import ClientGetter


def test_get_current_user(
    set_up_test_db: None,
    get_client: ClientGetter,
    test_user: User,
):
    with get_client(app, user=test_user) as client:
        res = client.get("/api/v1/users/current/")
        assert res.status_code == 200
        assert res.json() == {
            "uid": test_user.uid,
            "email": test_user.email,
            "nickname": test_user.nickname,
        }


def test_get_current_user_is_the_demo_user_when_not_overridden(
    set_up_test_db: None,
    get_client: ClientGetter,
    test_user: User,
):
    """Without a dependency override the user comes from DemoUserMiddleware,
    which the test client points at `user`."""
    with get_client(app, user=test_user) as client:
        app.dependency_overrides.pop(deps.current_user)
        res = client.get("/api/v1/users/current/")
    assert res.status_code == 200
    assert res.json() == {
        "uid": test_user.uid,
        "email": test_user.email,
        "nickname": test_user.nickname,
    }
