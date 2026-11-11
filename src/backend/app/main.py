from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from src.backend.app import errors
from src.backend.app.config import settings
from src.backend.app.middleware import (
    CatchallExceptionMiddleware,
    DemoUserMiddleware,
    OrgHeaderMiddleware,
    RequestContextMiddleware,
    RequestIdMiddleware,
    ServerTimingMiddleware,
)
from src.backend.app.routers.api_v2.commodity_location import (
    commodity_location_api_v2_router,
)
from src.backend.app.routers.change_set import change_set_router
from src.backend.app.routers.organisation import organisation_router
from src.backend.app.routers.permission import permission_router
from src.backend.app.routers.user import user_router

logger = settings.logger


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="backend service",
    description="A Python REST API that acts as the data & business logic layer for the dashboard.",
    debug=settings.DEBUG,
    version="0.0.0",
    lifespan=lifespan,
)

# The order of middleware is important; the last middleware added is the first to be executed.
app.add_middleware(GZipMiddleware, minimum_size=1000)
errors.add_exception_handlers(app)
app.add_middleware(OrgHeaderMiddleware)
app.add_middleware(DemoUserMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(CatchallExceptionMiddleware)
app.add_middleware(ServerTimingMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


api_router_v1 = APIRouter(prefix="/v1")
# Keep alphabetical order
api_router_v1.include_router(change_set_router)
api_router_v1.include_router(organisation_router)
api_router_v1.include_router(permission_router)
api_router_v1.include_router(user_router)


@app.get("/health", tags=["root"])
def health():
    """Unauthenticated liveness/health-check endpoint."""
    return {"status": "ok"}


app.include_router(
    api_router_v1,
    prefix=settings.API_PREFIX,
)

api_v2_router = APIRouter(prefix="/v2")
api_v2_router.include_router(commodity_location_api_v2_router)

app.include_router(
    api_v2_router,
    prefix=settings.API_PREFIX,
)
