import uuid
from datetime import datetime, timezone
from typing import Self

from pydantic import (
    AwareDatetime,
    Field,
    NonNegativeInt,
    field_validator,
    model_validator,
)
from src.backend.app.schemas.base import BasePlainSchema, BaseSchema
from src.backend.app.util.enums import (
    ChangeSetState,
    DataCoverage,
    UnitOfAnalysis,
)


class ParentChangeSet(BasePlainSchema):
    """Compact parent change set payload for ChangeSet responses."""

    uid: uuid.UUID
    name: str | None = None


class ChangeSetRead(BaseSchema):
    """Schema for returning a ChangeSet from the REST API."""

    org_uid: uuid.UUID
    parent_uid: uuid.UUID | None = None
    parent_change_set: ParentChangeSet | None = None
    state: ChangeSetState
    processed_at: AwareDatetime | None = None
    published_at: AwareDatetime | None = None
    unpublished_at: AwareDatetime | None = None
    name: str | None = None
    description: str | None = None
    is_latest: bool = Field(
        default=False,
        description=(
            "Whether this is the organisation's most recent change set."
            "Computed against the true leaf regardless of who is asking, so a "
            "caller who cannot see the leaf sees is_latest false on every "
            "change set they can — which is what tells the client that "
            "editing is unavailable, without disclosing the hidden version."
        ),
    )
    commodity_spend_coverage: DataCoverage | None = Field(
        default=None,
        description=(
            "Whether all, some or none of the change set's commodity "
            "locations have spend, from its datashape. Null when it has no "
            "datashape."
        ),
    )

    @field_validator(
        "processed_at", "published_at", "unpublished_at", mode="before"
    )
    @classmethod
    def add_timezone_to_dates(
        cls,
        v: AwareDatetime | str | None,
    ) -> AwareDatetime | None:
        if v is None:
            return None
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class UnitOfAnalysisChangeSummary(BaseSchema):
    """Schema for a holding unit of analysis level summary information"""

    value: float
    text: str


class UnitOfAnalysisChangeSummaryBreakdown(BaseSchema):
    """Schema for unit of analysis summary information by breakdown type"""

    regions: list[UnitOfAnalysisChangeSummary] = Field(default_factory=list)
    commodities: list[UnitOfAnalysisChangeSummary] = Field(default_factory=list)
    suppliers: list[UnitOfAnalysisChangeSummary] = Field(default_factory=list)
    products: list[UnitOfAnalysisChangeSummary] = Field(default_factory=list)


class ChangeSetSummary(BaseSchema):
    """Schema for returning a summary of a ChangeSet from the REST API."""

    org_uid: uuid.UUID
    change_set_uid: uuid.UUID
    state: ChangeSetState
    name: str | None = None
    description: str | None = None
    unit_of_analysis_summaries: dict[
        UnitOfAnalysis, UnitOfAnalysisChangeSummaryBreakdown
    ]


class ChangeSetDataShape(BasePlainSchema):
    """What data a change set holds, stored on `change_set.datashape`.

    Counted over the commodity locations alive as of the change set, each
    read from its exported row current as of that change set. The coverage
    flag is true only when there is at least one commodity location and
    every one of them has spend.
    """

    commodity_location_count: NonNegativeInt
    commodity_locations_with_spend_count: NonNegativeInt
    full_commodity_spend_coverage: bool

    @model_validator(mode="after")
    def counts_and_flags_agree(self) -> Self:
        if (
            self.commodity_locations_with_spend_count
            > self.commodity_location_count
        ):
            raise ValueError(
                "commodity_locations_with_spend_count exceeds"
                " commodity_location_count"
            )
        if self.full_commodity_spend_coverage != (
            self.commodity_location_count > 0
            and self.commodity_locations_with_spend_count
            == self.commodity_location_count
        ):
            raise ValueError(
                "full_commodity_spend_coverage does not match the commodity"
                " location counts"
            )
        return self


def commodity_spend_coverage(shape: ChangeSetDataShape) -> DataCoverage:
    """FULL when every commodity location has spend, NONE when none does
    (including when there are no commodity locations), PARTIAL otherwise."""
    if shape.full_commodity_spend_coverage:
        return DataCoverage.FULL
    if shape.commodity_locations_with_spend_count == 0:
        return DataCoverage.NONE
    return DataCoverage.PARTIAL
