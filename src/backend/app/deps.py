from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from src.backend.app.access import Access, SafeSession
from src.backend.app.config import settings
from src.backend.app.database import DB, DatabaseFactory, Session
from src.backend.app.middleware import ORG_UID_HEADER
from src.backend.app.schemas.organisation import OrganisationDB
from src.backend.app.schemas.permission.policy_document import policy_document
from src.backend.app.schemas.user import User
from src.backend.app.util import context

logger = settings.logger


def database_factory() -> DatabaseFactory:
    return DB


def get_unsafe_session(
    database_factory: Annotated[DatabaseFactory, Depends(database_factory)],
) -> Generator[Session]:
    """
    Gets a session that is not tied to a user's `Access`.
    """
    yield from database_factory.get_session()


def current_user() -> User:
    """
    Used by endpoints that should enforce that there is a user set in the request context.
    """
    user: User | None = context.get_current_user()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No user found",
        )
    return user


def access(
    user: Annotated[User, Depends(current_user)],
    database_factory: Annotated[DatabaseFactory, Depends(database_factory)],
) -> Access:
    """
    A class for performing role-based access control checks for the user based on the
    policies in the policy document.
    """
    return Access(policy_document, user, database_factory)


def get_safe_session(
    access: Annotated[Access, Depends(access)],
) -> Generator[SafeSession]:
    with access.get_session() as session:
        yield session


def current_org(
    safe_session: Annotated[SafeSession, Depends(get_safe_session)],
    org_uid: Annotated[str, Header(alias=ORG_UID_HEADER)],
) -> OrganisationDB:
    """
    Used by endpoints that should enforce that there is both a user and an org set in
    the request context.
    """
    # Importing here to avoid circular imports
    from src.backend.app.api.v1 import organisation

    try:
        org = organisation.get_organisation(
            safe_session, UUID(org_uid, version=4)
        )

        if org is None:
            missing_org_error = ValueError(
                f"Organisation not found with UUID: {org_uid}"
            )
            raise missing_org_error
    except ValueError as e:
        logger.exception(f"Organisation not found with UUID: {org_uid}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organisation UID",
        ) from e

    context.set_context("org", org)
    return org
