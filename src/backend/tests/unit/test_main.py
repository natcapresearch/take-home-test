import pytest
from fastapi import status
from pydantic import ValidationError
from src.backend.app.main import app
from src.backend.conftest import ClientGetter


def _remove_route(path: str) -> None:
    app.router.routes[:] = [
        route
        for route in app.router.routes
        if getattr(route, "path", None) != path
    ]
    app.openapi_schema = None


@pytest.fixture
def mock_error_500():
    @app.get("/500")
    def raise_exception():
        raise ValueError("This is a test")

    yield raise_exception
    _remove_route("/500")


@pytest.fixture
def mock_error_422():
    @app.get("/422")
    def raise_exception(a_param: int):
        raise ValidationError([])

    yield raise_exception
    _remove_route("/422")


def test_health(get_client: ClientGetter):
    with get_client(app, no_auth=True) as client:
        res = client.get("/health")
    assert res.status_code == status.HTTP_200_OK
    assert res.json() == {"status": "ok"}


def test_exception_handler(get_client: ClientGetter, mock_error_500: None):
    with get_client(app) as client:
        res = client.get("/500")
    assert res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    res = res.json()
    assert res["status"] == "error"
    assert res["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_validation_handler(get_client: ClientGetter, mock_error_422: None):
    with get_client(app) as client:
        res = client.get("/422", params={"random_param": "unexpected value"})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    res = res.json()
    assert res["status"] == "error"
    assert res["status_code"] == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_404(get_client: ClientGetter):
    with get_client(app) as client:
        res = client.get("/spurious")
    assert res.status_code == status.HTTP_404_NOT_FOUND
    res = res.json()
    assert res["status"] == "error"
    assert res["status_code"] == status.HTTP_404_NOT_FOUND


def test_openapi_lists_exactly_the_kept_routes():
    app.openapi_schema = None
    assert sorted(app.openapi()["paths"]) == [
        "/api/v1/change-set/",
        "/api/v1/change-sets/",
        "/api/v1/change-sets/{change_set_uid}/",
        "/api/v1/change-sets/{change_set_uid}/summary/",
        "/api/v1/object-permission-set/root/",
        "/api/v1/object-permission-set/{obj}/{uid}/",
        "/api/v1/organisations/{org_uid}/",
        "/api/v1/users/current/",
        "/api/v2/commodity-source-regions-aggregated/",
        "/api/v2/commodity-sources/",
        "/api/v2/commodity-summary/",
        "/health",
    ]
