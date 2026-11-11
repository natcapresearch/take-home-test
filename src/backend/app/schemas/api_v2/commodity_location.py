from typing import Literal

from pydantic import UUID4, Field
from src.backend.app.schemas.api_v2.request import ChangeSetListQueryParams
from src.backend.app.schemas.base import PydanticSchema
from src.backend.app.util.enums import EntityScope, SortOrder

# Named after the response fields (ChangeSetCommoditySourceRead), not the
# columns: api/v2/commodity_location.py maps each key to its column.
CommodityLocationSortKey = Literal[
    "identifier",
    "commodity_type",
    "commodity_subgroup",
    "commodity_code",
    "year_purchased",
    "sourcing_country",
    "sourcing_region",
    "spend",
    "quantity_kilograms",
    "supplier",
    "product",
]


class ChangeSetCommodityLocationQueryParams(ChangeSetListQueryParams):
    sort_on: CommodityLocationSortKey = Field(default="identifier")
    # DESC kept from the endpoint's previous default, so callers that send no
    # sort_order see no change in ordering.
    sort_order: SortOrder = Field(default=SortOrder.DESC)
    commodity_subgroup: str | None = Field(default=None)
    # Exact-name filter, as sent by the typeahead pickers once a suggestion
    # is chosen. commodity_subgroup above is the substring match behind those
    # suggestions; both are accepted.
    commodity_subgroups: list[str] | None = Field(default=None)
    countries: list[str] | None = Field(default=None)
    sourcing_administrative_level_1_names: list[str] | None = Field(
        default=None
    )
    suppliers: list[str] | None = Field(default=None)
    product_names: list[str] | None = Field(default=None)
    scope: EntityScope = Field(default=EntityScope.ALIVE)


class ChangeSetCommodityRegionQueryParams(PydanticSchema):
    change_set_uid: UUID4
    commodity_subgroups: list[str] | None = Field(
        default=None,
        description="Filter to specific commodity subgroups",
    )
    include_geometry: bool = Field(
        default=False,
        description="When true, return each location's AdminRegion geojson; omit for fast geometry-free responses",
    )
    group_by_country: bool = Field(
        default=False,
        description="When true, sum admin-1 regions into their country: one row per country, with the country's geometry",
    )
