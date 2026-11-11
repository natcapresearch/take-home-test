from fastapi import APIRouter, Depends
from src.backend.app import deps
from src.backend.app.config import settings
from src.backend.app.schemas.user import User, UserResponse

logger = settings.logger

user_router = APIRouter(
    tags=["user"],
)


@user_router.get(
    "/users/current/", summary="Get current user", response_model=UserResponse
)
def get_current_user(
    user: User = Depends(deps.current_user),
):
    return user
