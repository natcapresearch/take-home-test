# pyright: reportUnusedFunction=false

import time
import uuid
from collections.abc import Callable
from typing import Any

import structlog
from fastapi import HTTPException, Request, status
from src.backend.app.config import settings
from src.backend.app.schemas.response import JsonResponse
from src.backend.app.schemas.user import User
from src.backend.app.util import context
from src.backend.app.util.context import set_context
from starlette.middleware.base import BaseHTTPMiddleware

logger = settings.logger

ORG_UID_HEADER = "x-org-uid"


class ServerTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> JsonResponse:
        """
        Add a Server-Timing header to the response to show the time taken to process the request.
        https://developer.mozilla.org/en-US/docs/Web/API/Performance_API/Server_timing
        """
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["Timing-Allow-Origin"] = ",".join(
            settings.BACKEND_CORS_ALLOWED_ORIGINS
        )
        response.headers["Server-Timing"] = (
            f"backend;dur={process_time:.2f};desc='Backend total'"
        )
        response_bytes = response.headers.get("content-length", "?")
        logger.info(
            f'"{request.method} {request.url.path}" - HTTP {response.status_code} in {process_time * 1000:.2f}ms',
            **{"response_bytes": response_bytes},
        )
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> JsonResponse:
        """
        Bind a short `request_id` onto structlog contextvars for the lifetime
        of one HTTP request so every log line emitted during handling carries
        the same correlation id. Cleared on the way out so contextvars don't
        leak between requests.
        """
        request_id = uuid.uuid4().hex[:12]
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            return await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")


class OrgHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> JsonResponse:
        """
        Just checks that if the organisation header is present, it is a valid UUIDv4.
        """
        org_header: str | None = request.headers.get(ORG_UID_HEADER)
        if org_header is None:
            return await call_next(request)

        try:
            org_uid = uuid.UUID(org_header, version=4)

            # Check that the UUID was in fact a UUIDv4 and not a silently-accepted different version
            if str(org_uid) != org_header:
                org_uid_value_error = ValueError("Invalid organisation UUID")
                raise org_uid_value_error
        except ValueError:
            logger.exception(
                f"Invalid organisation UUID in request headers: {org_header}"
            )
            return JsonResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": f"{ORG_UID_HEADER} header must be a valid UUIDv4",
                    "status": "error",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
            )

        return await call_next(request)


class DemoUserMiddleware(BaseHTTPMiddleware):
    """Runs every request as the single demo user configured in settings.

    There is no login: the user's identity and roles come from the
    `DEMO_USER_*` settings, and the roles decide which policies in
    policy_document.yaml apply.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> JsonResponse:
        set_context(
            "user",
            User(
                uid=f"demo|{settings.DEMO_USER_EMAIL}",
                email=settings.DEMO_USER_EMAIL,
                nickname=settings.DEMO_USER_NICKNAME,
                roles=settings.demo_user_roles,
            ),
        )
        return await call_next(request)


class CatchallExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> JsonResponse:
        """Catch all exceptions in order to return a JSON response"""
        try:
            return await call_next(request)
        except HTTPException as e:
            return JsonResponse(
                status_code=e.status_code,
                content={
                    "detail": e.detail,
                    "status": "error",
                    "status_code": e.status_code,
                },
            )
        except Exception as e:
            logger.exception(str(e))  # noqa: TRY401

            msg = "Internal server error"
            if settings.DEBUG:
                msg = f"{msg}: {e}"

            return JsonResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": msg,
                    "status": "error",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                },
            )


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> JsonResponse:
        """Reset the request context for the new request"""
        context.reset_context()
        return await call_next(request)
