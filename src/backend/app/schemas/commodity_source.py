import uuid

from pydantic import (
    Field,
)
from src.backend.app.schemas.base import BasePlainSchema
from src.backend.app.schemas.geojson import GeoJSONGeometry


class CommoditySourceSummary(BasePlainSchema):
    """Summary statistics for commodity sources."""

    total_commodities: int = Field(
        description="Number of distinct commodity subgroups"
    )
    commodity_types: list[str] = Field(
        default_factory=list,
        description="Distinct commodity types available for filtering",
    )
    commodity_subgroups: list[str] = Field(
        default_factory=list,
        description="Distinct commodity subgroups available for filtering",
    )
    sourcing_countries: list[str] = Field(
        default_factory=list,
        description="Distinct sourcing countries available for filtering",
    )
    sourcing_regions: list[str] = Field(
        default_factory=list,
        description="Distinct sourcing regions available for filtering",
    )
    supplier_names: list[str] = Field(
        default_factory=list,
        description="Distinct supplier names available for filtering",
    )
    product_names: list[str] = Field(
        default_factory=list,
        description="Distinct product names available for filtering",
    )
    total_suppliers: int = Field(description="Number of distinct suppliers")
    total_locations: int = Field(
        description="Number of distinct sourcing locations (country level)"
    )
    total_spend: int | None = Field(
        description="Total spend across all sources; null when no source has spend"
    )
    total_quantity: float | None = Field(
        description="Total quantity in kilograms across all sources; null when no source has quantity"
    )
    all_commodities_have_quantity: bool | None = Field(
        default=None,
        description="True when every commodity source has quantity_kilograms. NULL for empty set.",
    )
    all_commodities_have_spend: bool | None = Field(
        default=None,
        description="True when every commodity source has spend. NULL for empty set.",
    )
    missing_quantity_count: int = Field(
        default=0,
        description="Number of commodity sources missing quantity_kilograms",
    )
    missing_spend_count: int = Field(
        default=0,
        description="Number of commodity sources missing spend",
    )
    total_commodity_sources: int = Field(
        default=0,
        description=(
            "Total number of commodity source rows this missing_*_count is "
            "counted out of - lets a consumer tell 'none have this field' "
            "(missing == total) apart from 'some are missing it' (partial)."
        ),
    )


class CommodityBreakdownEntry(BasePlainSchema):
    """Single commodity's contribution within an aggregated region."""

    commodity_subgroup: str
    total_spend: float = Field(
        description="Spend for this commodity in the region"
    )
    total_quantity: float = Field(
        description="Quantity in kilograms for this commodity in the region"
    )


class AggregatedCommoditySourceRegion(BasePlainSchema):
    """Commodity source region aggregated by location with nested commodity breakdown."""

    country_name: str
    sourcing_administrative_level_1_name: str | None = Field(default=None)
    total_spend: float = Field(
        description="Total spend across all commodities in this region"
    )
    total_quantity: float = Field(
        description="Total quantity in kilograms across all commodities in this region"
    )
    geometry: GeoJSONGeometry | None = Field(
        default=None,
        description="GeoJSON geometry for the sourcing location",
    )
    commodity_breakdown: list[CommodityBreakdownEntry] = Field(
        default_factory=list,
        description="Per-commodity spend and quantity breakdown",
    )


class ChangeSetCommoditySourceRead(BasePlainSchema):
    """Changeset-aware commodity source read schema."""

    entity_uid: uuid.UUID
    org_uid: uuid.UUID
    identifier: str
    commodity_type: str
    commodity_subgroup: str
    commodity_code: str
    year_purchased: int
    sourcing_country: str | None = None
    sourcing_region: str | None = None
    quantity_kilograms: float | None = None
    spend: float | None = None
    supplier: str | None = None
    product: str | None = None
    alive_in_change_set: bool = Field(
        default=True,
        description=(
            "False when the entity is not alive in the requested changeset."
            " Only ever False for scope=all listings, which return entities"
            " outside the changeset so a caller can show them as not in this"
            " version rather than omitting them."
        ),
    )
