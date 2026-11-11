from fastapi import APIRouter, Depends
from pydantic import UUID4
from src.backend.app import deps
from src.backend.app.access import Access
from src.backend.app.config import settings
from src.backend.app.schemas.permission.permission_set_read import (
    PermissionSetRead,
)

logger = settings.logger

permission_router = APIRouter(
    tags=["permission"],
)


@permission_router.get(
    "/object-permission-set/root/",
    response_model=PermissionSetRead,
)
def get_root_object_permission_set(
    access: Access = Depends(deps.access),
) -> PermissionSetRead:
    """Get the permission set for the root object."""
    return PermissionSetRead(
        object="root", roles=[], scopes=access.get_actions("root", None)
    )


@permission_router.get(
    "/object-permission-set/{obj}/{uid}/",
    response_model=PermissionSetRead,
)
def get_id_object_permission_set(
    obj: str, uid: UUID4, access: Access = Depends(deps.access)
) -> PermissionSetRead | None:
    """Get the permission set for an object with an ID."""
    return PermissionSetRead(
        object=f"{obj}:{uid}", roles=[], scopes=access.get_actions(obj, uid)
    )
