"""
The dashboard web server: serves the built SPA from `dist/` (with an
index.html fallback for client-side routes) and reverse-proxies `/api` to the
GraphQL server.

Settings (environment variables):
- GRAPHQL_PROXY_URL: the GraphQL server to proxy `/api` to, e.g.
  http://localhost:4000. The `/api` mount is omitted when unset.
- GRAPHQL_PROXY_TIMEOUT: proxy request timeout in seconds (default 5).
- STATIC_FILE_DELAY: seconds to delay static responses by (default 0); helps
  the Parcel dev server not skip updates on a full-page reload.
"""

import abc
import asyncio
import html
import logging
import os
from dataclasses import dataclass
from os import PathLike, stat_result
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.routing import Mount
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    GRAPHQL_PROXY_URL: str | None = os.environ.get("GRAPHQL_PROXY_URL") or None
    GRAPHQL_PROXY_TIMEOUT: int = int(
        os.environ.get("GRAPHQL_PROXY_TIMEOUT", "5")
    )
    STATIC_FILE_DELAY: float = float(os.environ.get("STATIC_FILE_DELAY", "0"))


ERROR_TEMPLATE = Path("src/ui/dashboard/error.html")

settings = Settings()


class StaticFilesWithIndexFallback(StaticFiles):
    # https://github.com/tiangolo/fastapi/issues/858#issuecomment-876564020
    def __init__(
        self, directory: PathLike, index: str, *args, **kwargs
    ) -> None:
        self.index = index
        super().__init__(
            *args,
            directory=directory,
            packages=None,
            html=True,
            check_dir=True,
            **kwargs,
        )

    async def get_response(self, path, scope):
        if settings.STATIC_FILE_DELAY:
            await asyncio.sleep(settings.STATIC_FILE_DELAY)
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse) and str(response.path).endswith(
            self.index
        ):
            # index.html must never be cached: a stale copy references old
            # hashed bundle filenames, causing a blank screen after deploys.
            # NOTE: we check response.path (not lookup_path(path)) because for
            # GET / the path is "", and lookup_path("") returns the directory
            # stat, causing the wrong branch to be taken and index.html to
            # receive the immutable header instead.
            response.headers["Cache-Control"] = (
                "no-cache, no-store, must-revalidate"
            )
        elif isinstance(response, FileResponse):
            # Content-addressed assets (hashed filenames) are immutable, so
            # safe to cache for 1 year.
            response.headers["Cache-Control"] = (
                "public, max-age=31536000, immutable"
            )
        return response

    # Extensions that should never fall back to index.html: a missing asset
    # should surface as a real 404, not silently return HTML (which causes
    # "Expected a JavaScript module but server responded with text/html" errors).
    _ASSET_EXTENSIONS = {
        ".js",
        ".mjs",
        ".css",
        ".map",
        ".json",
        ".wasm",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".webp",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
    }

    def lookup_path(self, path: str) -> tuple[str, stat_result | None]:
        """Returns the index file when no match is found, except for asset files."""

        full_path, stat_result = super().lookup_path(path)

        if stat_result is None:
            suffix = Path(path).suffix.lower()
            if suffix not in self._ASSET_EXTENSIONS:
                return super().lookup_path(self.index)

        return (full_path, stat_result)


async def handle_error(request: Request, exc: Exception):
    status_code, error, error_description = (
        500,
        "Unknown error",
        "An unknown error occurred",
    )
    if isinstance(exc, HTTPException):
        status_code, error, error_description = (
            exc.status_code,
            str(exc.status_code),
            exc.detail,
        )

    page = (
        ERROR_TEMPLATE.read_text()
        .replace("{{error}}", html.escape(str(error)))
        .replace("{{error_description}}", html.escape(str(error_description)))
    )
    return HTMLResponse(page, status_code=status_code)


class ASGIEndpoint(abc.ABC):
    """
    An abstract base class that implements the ASGI interface, wrapping around a
    `handler` method.

    This is used instead of the Starlette and FastAPI function-based handlers because it
    allows instance properties to be type-checked and set at the point the routes are
    defined.
    """

    @abc.abstractmethod
    async def handler(self, request) -> Response: ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        request = Request(scope, receive)
        response = await self.handler(request)
        await response(scope, receive, send)


class ReverseProxy(ASGIEndpoint):
    def __init__(self, target_base: str, timeout: int = 5):
        self.client = httpx.AsyncClient(
            base_url=target_base,
            timeout=httpx.Timeout(timeout),
        )

    # Adapted from:
    # https://github.com/fastapi/fastapi/issues/1788#issuecomment-1071222163
    async def handler(self, request: Request):
        url = httpx.URL(
            path=request.url.path, query=request.url.query.encode("utf-8")
        )
        proxy_request = self.client.build_request(
            request.method,
            url,
            headers=request.headers.raw,
            content=await request.body(),
        )
        proxy_response = await self.client.send(proxy_request, stream=True)
        return StreamingResponse(
            proxy_response.aiter_raw(),
            status_code=proxy_response.status_code,
            headers=proxy_response.headers,
            background=BackgroundTask(proxy_response.aclose),
        )


class Health(ASGIEndpoint):
    async def handler(self, request: Request) -> Response:
        return Response("Okay!", status_code=200)


# Route-handling order is from top-to-bottom.
app = FastAPI(
    docs_url=None,
    redoc_url=None,
    exception_handlers={Exception: handle_error},
    routes=[
        *(
            [
                Mount(
                    "/api",
                    app=ReverseProxy(
                        target_base=settings.GRAPHQL_PROXY_URL,
                        timeout=settings.GRAPHQL_PROXY_TIMEOUT,
                    ),
                )
            ]
            if settings.GRAPHQL_PROXY_URL
            else []
        ),
        Route("/health", Health()),
        Mount(
            "/public",
            app=StaticFiles(directory=Path("src/ui/dashboard/public")),
        ),
        Mount(
            "/",
            app=StaticFilesWithIndexFallback(
                directory=Path("dist"), index="index.html"
            ),
        ),
    ],
)
