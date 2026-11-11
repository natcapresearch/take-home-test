import datetime
import uuid
from typing import Annotated, Any

from pydantic import (
    AnyUrl,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    Field,
    TypeAdapter,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel
from pydantic.config import ConfigDict
from pydantic_core import PydanticUseDefault

# A URL type built on top of Pydantic's AnyUrl that allows Urls to be treated like strings
http_url_adapter = TypeAdapter(AnyUrl)
Url = Annotated[
    str, BeforeValidator(lambda x: str(http_url_adapter.validate_python(x)))
]


class PydanticSchema(BaseModel):
    """A convenience class to making naming clearer (models are DB)"""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class BaseSchema(PydanticSchema):
    """Base Pydantic schema all schemas should inherit from."""

    uid: uuid.UUID = Field(default_factory=uuid.uuid4)

    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc),
    )
    updated_at: AwareDatetime = Field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc)
    )

    meta: dict[str, Any] = Field(
        default_factory=dict, serialization_alias="_meta"
    )

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def add_timezone(cls, v: AwareDatetime | str | None) -> AwareDatetime:
        if v is None:
            raise PydanticUseDefault()
        if isinstance(v, str):
            v = datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
        if v.tzinfo is None:
            # DateTimes are stored in the database as UTC "timezone unaware" ie without
            # a timezone component, so we need to add the timezone info back in before
            # as Pydantic expects all datetimes to be timezone aware
            return v.replace(tzinfo=datetime.timezone.utc)
        return v

    @model_validator(mode="after")
    def add_cursor_to_model(self, info: ValidationInfo):
        context = info.context
        is_read_schema = self.__class__.__name__.endswith("Read")
        if is_read_schema and context and context.get("metadata"):
            self.meta.update(context["metadata"])
        return self

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class BasePlainSchema(PydanticSchema):
    """
    Base Pydantic schema for objects that are 'plain', such as create/edit
    objects and objects not stored in the database.

    This allows for such objects to be validated, but authors don't need to set
    the `uid`, `created_at`, or `updated_at` fields required by BaseSchema.
    These fields are therefore not included in this schema.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
