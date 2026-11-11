import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from src.backend.app.errors.handlers import (
    make_exception_handler,
    not_found_exception_handler,
    validation_exception_handler,
)


@pytest.fixture(scope="function")
def mock_request() -> Request:
    return Request(scope={"type": "http"})


def test_make_exception_handler(mock_request: Request):
    handler = make_exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR)
    exc = Exception("Test exception")
    response = handler(mock_request, exc)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.content.model_dump() == {
        "detail": "Test exception",
        "status": "error",
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }


def test_not_found_exception_handler(mock_request: Request):
    exc = Exception("Not Found")
    response = not_found_exception_handler(mock_request, exc)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.content.model_dump() == {
        "detail": "Not Found",
        "status": "error",
        "status_code": status.HTTP_404_NOT_FOUND,
    }


def test_validation_exception_handler(mock_request: Request):
    exc = RequestValidationError(
        [{"loc": ["body"], "msg": "Invalid input", "type": "value_error"}]
    )
    response = validation_exception_handler(mock_request, exc)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.content.model_dump() == {
        "detail": exc.errors(),
        "status": "error",
        "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
    }


def test_validation_exception_handler_non_validation_error(
    mock_request: Request,
):
    exc = Exception("Non-validation error")
    with pytest.raises(Exception) as exc_info:
        validation_exception_handler(mock_request, exc)
    assert str(exc_info.value) == "Non-validation error"
