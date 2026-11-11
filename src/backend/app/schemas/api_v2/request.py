from typing import Any

from pydantic import UUID4, Field, field_validator, model_validator
from src.backend.app.config import settings
from src.backend.app.schemas.base import PydanticSchema
from src.backend.app.util.pagination import PaginationCursor, PaginationError


def has_param(data: Any, name: str) -> bool:
    """Whether the raw params carry `name`. Undeclared params are otherwise
    dropped without an error, so a list validates them before parsing."""
    return isinstance(data, dict) and name in data


class ListQueryParams(PydanticSchema):
    """Base query params for API v2 list endpoints: cursors and page size.

    Versioned listings use `ChangeSetListQueryParams` below.

    Deliberately declares no `sort_on` / `sort_order`: each subclass declares
    both, with its own `Literal[...]` allowlist and defaults, so no field is
    ever overridden with a narrower type. Not a `CommonQueryParams` subclass
    for the same reason; the cursor handling below mirrors it.
    """

    before: PaginationCursor | None = Field(default=None)
    after: PaginationCursor | None = Field(default=None)
    limit: int = Field(
        default=settings.DEFAULT_PAGE_SIZE,
        gt=0,
        le=settings.MAX_PAGE_SIZE,
    )

    @field_validator("before", "after", mode="before")
    @classmethod
    def parse_cursor(
        cls, val: PaginationCursor | str | None
    ) -> PaginationCursor | str | None:
        if val == "":
            val = None
        return val

    @model_validator(mode="after")
    def validate_cursors(self):
        if self.before and self.after:
            raise PaginationError(
                "Cannot specify both before and after cursors"
            )
        return self


class ChangeSetListQueryParams(ListQueryParams):
    """Base query params for API v2 list endpoints that read data as of a
    change set."""

    change_set_uid: UUID4
