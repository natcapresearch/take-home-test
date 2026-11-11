import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from src.backend.app.errors import add_exception_handlers, handle
from src.backend.app.errors.registry import registry
from src.backend.app.schemas.response import JsonResponse
from src.backend.conftest import ClientGetter


@pytest.fixture(scope="function")
def app():
    app = FastAPI()
    yield app
    app.exception_handlers.clear()


@pytest.fixture
def client(app: FastAPI):
    return TestClient(app)


def test_add_exception_handlers(app: FastAPI):
    registry.clear()

    @handle(404)
    class NotFoundError(Exception):
        pass

    exception_handlers = app.exception_handlers
    assert len(exception_handlers) == 3

    add_exception_handlers(app)

    assert len(app.exception_handlers) == 4
    assert NotFoundError in app.exception_handlers


def test_handle_with_handler():
    registry.clear()

    def custom_handler(request: Request, exc: Exception) -> JsonResponse:
        return JsonResponse(
            status_code=400, content={"message": "Custom error"}
        )

    @handle(custom_handler)
    class CustomError(Exception):
        pass

    assert (CustomError, custom_handler) in registry


def test_custom_exception_handler(get_client: ClientGetter):
    from src.backend.app.main import app

    registry.clear()

    @handle(404)
    class NotFoundError(Exception):
        pass

    add_exception_handlers(app)

    @app.get("/raise-not-found")
    def raise_not_found():  # type: ignore
        raise NotFoundError()

    try:
        with get_client(app) as client:
            response = client.get("/raise-not-found")
    finally:
        app.router.routes[:] = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) != "/raise-not-found"
        ]
        app.openapi_schema = None
    assert response.status_code == 404
