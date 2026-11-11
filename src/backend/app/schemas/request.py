from typing import Literal

from pydantic import Field, field_validator, model_validator
from src.backend.app.config import settings
from src.backend.app.schemas.base import BasePlainSchema, PydanticSchema
from src.backend.app.util.enums import ChangeSetState, SortOrder
from src.backend.app.util.pagination import PaginationCursor, PaginationError

logger = settings.logger


class CommonQueryParams(PydanticSchema):
    sort_on: str | None = Field(default=None)
    sort_order: SortOrder = Field(default=SortOrder.DESC)
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
    def validate_params(self):
        if (
            self.before is not None or self.after is not None
        ) and self.sort_on is not None:
            logger.debug(
                "After/before cursor will take precedence over sort_on"
            )

        if self.before and self.after:
            raise PaginationError(
                "Cannot specify both before and after cursors"
            )

        return self


class ChangeSetsQueryParams(CommonQueryParams):
    state: ChangeSetState | None = Field(default=None)


class ChangeSetUpdate(BasePlainSchema):
    """Request body for patching a change set.

    All fields are optional. State transitions must follow the allowed state
    transition rules defined in the backend API.
    """

    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    state: Literal["draft", "processing", "done", "published"] | None = Field(
        default=None
    )
