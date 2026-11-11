from collections.abc import Callable

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from src.backend.app.config import settings
from src.backend.app.schemas.response import JsonResponse

logger = settings.logger


def make_exception_handler(
    code: int,
    detail: str | None = None,
    detail_factory: Callable[[Exception], dict[str, str]] | None = None,
) -> Callable[[Request, Exception], JsonResponse]:
    """Returns an exception handler that generates a JSON response with the given status code and detail message.

    If detail_factory is provided, it will be called with the exception to generate a detail dictionary for the response.

    Args:
        code: The HTTP status code for the response.
        detail: A default detail message for the response. Ignored if detail_factory is provided.
        detail_factory: An optional callable that takes an exception and returns a dictionary to be used as the detail in the response.

    Returns: A callable exception handler that can be used with FastAPI.
    """

    def exception_handler(request: Request, exc: Exception) -> JsonResponse:
        if detail_factory is not None:
            _detail: str | dict[str, str] = detail_factory(exc)
        else:
            _detail = detail or str(exc)
        return JsonResponse(
            status_code=code,
            content=jsonable_encoder(
                {
                    "detail": _detail,
                    "status": "error",
                    "status_code": code,
                }
            ),
        )

    return exception_handler


not_found_exception_handler = make_exception_handler(
    status.HTTP_404_NOT_FOUND, "Not Found"
)


def validation_exception_handler(
    request: Request, exc: Exception
) -> JsonResponse:
    """Returns a JSON response for Pydantic validation errors"""
    if not isinstance(exc, RequestValidationError):
        raise exc

    if settings.DEBUG:
        logger.debug(str(exc))

    return JsonResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "detail": exc.errors(),
                "status": "error",
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            }
        ),
    )
