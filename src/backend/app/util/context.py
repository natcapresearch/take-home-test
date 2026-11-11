from contextvars import ContextVar
from types import SimpleNamespace
from typing import Any

from src.backend.app.config import settings
from src.backend.app.database import Session
from src.backend.app.schemas.organisation import OrganisationDB
from src.backend.app.schemas.user import User

logger = settings.logger

request_context = ContextVar(
    "request_context",
    default=SimpleNamespace(db=None, user=None, org=None),
)


def reset_context():
    """Reset the request context."""
    request_context.set(SimpleNamespace(db=None, user=None, org=None))


def set_context(attr: str, value: Any):
    """Set a value in the request context."""
    context = request_context.get()
    setattr(context, attr, value)


def get_db() -> Session | None:
    """Get the configured database session from the request context."""
    context = request_context.get()
    db = getattr(context, "db", None)
    if db is None:
        logger.debug("Database not found in request context")
    return db


def get_current_user() -> User | None:
    """Get the current user from the request context."""
    context = request_context.get()
    user: User | None = getattr(context, "user", None)
    if user is None:
        logger.debug("User not found in request context")
    return user


def get_current_org() -> OrganisationDB | None:
    """Get the current org from the request context."""
    context = request_context.get()
    org: OrganisationDB | None = getattr(context, "org", None)
    if org is None:
        logger.debug("Organisation not found in request context")
    return org
