from pydantic import (
    UUID4,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
)
from pydantic.alias_generators import to_camel
from pydantic_core import PydanticUseDefault
from src.backend.app.schemas.base import (
    BasePlainSchema,
    BaseSchema,
)


class AnalysisYears(BasePlainSchema):
    """Holds the analysis years for an organisation."""

    base_year: int
    target_year: int


class OrganisationConfig(BasePlainSchema):
    """Represents the organisation configuration stored in the DB.

    Stored as JSONB with camelCase keys (`hasCommodityImpacts`, ...), which
    is also how the API serialises it.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    has_commodity_impacts: bool = Field(default=False)
    has_commodity_dependencies: bool = Field(default=False)
    has_commodity_risks: bool = Field(default=False)


class OrganisationBase(BaseSchema):
    """Base schema for organisations."""

    name: str
    description: str | None = Field(default=None)

    analysis_years: AnalysisYears | None = Field(
        default=None,
        description="""Holds the analysis years for an org.""",
    )

    config: OrganisationConfig | None = Field(
        default=None,
        description="""Holds the configuration/feature flag values for an org.""",
    )

    default_change_set_uid: UUID4 | None = Field(
        default=None,
    )


class OrganisationDB(OrganisationBase):
    """A DB-equivalent schema for organisations."""

    # Cannot be read directly — should not be available to Read schema
    authorised_email_domains: list[str] = Field(default_factory=list)

    @field_validator("authorised_email_domains", mode="before")
    @classmethod
    def set_empty_authorised_email_domains(
        cls, v: list[str] | None
    ) -> list[str]:
        """Ensure that authorised_email_domains is always a list."""
        if v is None:
            raise PydanticUseDefault()
        return v


class OrganisationRead(OrganisationBase):
    """Organisation schema for API responses."""

    @computed_field
    @property
    def slug(self) -> str:
        """Return the slugified version of the organisation name."""
        return self.name.replace(" ", "-").lower()
