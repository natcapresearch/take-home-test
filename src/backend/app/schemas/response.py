from typing import Any, Literal

from fastapi.responses import JSONResponse as FastApiJsonResponse
from pydantic import (
    ConfigDict,
    Field,
    field_validator,
)
from src.backend.app.config import settings
from src.backend.app.schemas.base import PydanticSchema
from src.backend.app.util.pagination import PaginationCursor

logger = settings.logger


class ResponseContent(PydanticSchema):
    """Used by the standardised JSONResponse schema for JSON responses from the API."""

    detail: str | dict[str, Any] | list[dict[str, Any]]
    status: Literal["success", "error"]
    status_code: int


class JsonResponse(PydanticSchema, FastApiJsonResponse):
    """Standard schema for JSON responses from the API."""

    status_code: int
    content: ResponseContent

    model_config = ConfigDict(extra="allow")

    def __init__(self, *args: Any, **kwargs: Any):
        PydanticSchema.__init__(self, *args, **kwargs)
        FastApiJsonResponse.__init__(self, *args, **kwargs)


class CommonResponseHeaders(PydanticSchema):
    next_cursor: PaginationCursor | str | None = Field(
        serialization_alias="natcap-next-cursor",
        default="",
    )
    prev_cursor: PaginationCursor | str | None = Field(
        serialization_alias="natcap-prev-cursor", default=""
    )
    total: int | str | None = Field(
        serialization_alias="natcap-total-count", default=""
    )

    @field_validator("next_cursor", "prev_cursor", mode="after")
    @classmethod
    def validate_cursor(
        cls, cursor: PaginationCursor | str | None
    ) -> PaginationCursor | str:
        if cursor is None:
            cursor = ""
        return cursor

    @field_validator("total", mode="after")
    @classmethod
    def validate_total(cls, total: int | str | None) -> str:
        if total is None:
            total = ""
        if isinstance(total, int):
            total = str(total)
        return total

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )
