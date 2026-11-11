from collections.abc import Callable

from fastapi import Request
from src.backend.app.errors.handlers import make_exception_handler
from src.backend.app.schemas.response import JsonResponse

Handler = Callable[[Request, Exception], JsonResponse]

registry: list[tuple[int | type[Exception], Handler]] = []


def register(cls_or_int: int | type[Exception], handler: Handler) -> None:
    """Register an exception handler for a specific exception class"""
    registry.append((cls_or_int, handler))


def handle(
    handler_or_int: int | Handler,
) -> Callable[[type[Exception]], type[Exception]]:
    """Decorator to register an exception handler for a specific exception class"""

    def decorator(cls: type[Exception]) -> type[Exception]:
        if isinstance(handler_or_int, int):
            register(cls, make_exception_handler(handler_or_int))
        else:
            register(cls, handler_or_int)
        return cls

    return decorator
