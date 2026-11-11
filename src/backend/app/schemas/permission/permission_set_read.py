from src.backend.app.schemas.base import PydanticSchema


class PermissionSetRead(PydanticSchema):
    object: str
    roles: list[str]
    scopes: list[str]
