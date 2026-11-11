from fastapi import status
from fastapi.exceptions import RequestValidationError
from src.backend.app.errors.handlers import (
    make_exception_handler,
    not_found_exception_handler,
    validation_exception_handler,
)
from src.backend.app.errors.registry import handle, register
from src.backend.app.util.pagination import PaginationError


@handle(status.HTTP_403_FORBIDDEN)
class NotAuthorisedError(Exception): ...


@handle(status.HTTP_400_BAD_REQUEST)
class OrganisationNotFoundError(Exception): ...


@handle(status.HTTP_409_CONFLICT)
class ChangeSetProcessingError(Exception):
    """Raised when an operation is attempted while a change set is processing."""

    ...


@handle(status.HTTP_404_NOT_FOUND)
class ChangeSetNotFoundError(Exception):
    """Raised when a change set cannot be found."""

    ...


# Add default exception handlers for built-in exceptions
register(RequestValidationError, validation_exception_handler)
register(404, not_found_exception_handler)
# A malformed cursor, or both `before` and `after`, is a bad request param.
# PaginationError is registered here rather than decorated with @handle where
# it is defined: util/pagination is imported by schemas/response, which the
# handlers module imports, so decorating it there would be circular.
register(
    PaginationError,
    make_exception_handler(status.HTTP_422_UNPROCESSABLE_ENTITY),
)
