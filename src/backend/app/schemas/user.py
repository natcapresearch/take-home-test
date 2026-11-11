from pydantic import EmailStr
from src.backend.app.schemas.base import BasePlainSchema


class User(BasePlainSchema):
    """The authenticated user for a request."""

    uid: str
    email: EmailStr
    nickname: str
    roles: list[str]


class UserResponse(BasePlainSchema):
    """Schema for the returned user response"""

    uid: str
    email: EmailStr
    nickname: str
