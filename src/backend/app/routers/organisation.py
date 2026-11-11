from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from pydantic import UUID4
from src.backend.app import deps
from src.backend.app.access import Access, SafeSession
from src.backend.app.api.v1 import organisation as organisation_v1
from src.backend.app.errors import NotAuthorisedError
from src.backend.app.schemas.organisation import (
    OrganisationDB,
    OrganisationRead,
)

organisation_router = APIRouter(
    tags=["organisations"],
)


@organisation_router.get(
    "/organisations/{org_uid}/", response_model=OrganisationRead
)
def get_organisation(
    org_uid: UUID4,
    safe_session: SafeSession = Depends(deps.get_safe_session),
    access: Access = Depends(deps.access),
) -> OrganisationDB:
    """Get a single organisation by UUID."""
    if not access.check("read:org:basic", org_uid):
        raise NotAuthorisedError(
            "Insufficient permissions to read this organisation."
        )
    is_admin = "admin" in access.user.roles
    org = organisation_v1.get_organisation(
        safe_session,
        org_uid,
        is_admin=is_admin,
    )
    if org is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Organisation not found",
        )
    return org
