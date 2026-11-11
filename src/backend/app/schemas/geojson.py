"""
Pydantic models for GeoJSON structures.
"""

from typing import Any, Literal

from pydantic import ConfigDict, Field
from src.backend.app.schemas.base import PydanticSchema


class GeoJSONGeometry(PydanticSchema):
    """GeoJSON geometry object."""

    model_config = ConfigDict(extra="allow")

    type: Literal["Polygon", "MultiPolygon"]
    coordinates: (
        list[list[tuple[float, float]]] | list[list[list[tuple[float, float]]]]
    )


class GeoJSONFeature(PydanticSchema):
    """A single GeoJSON feature."""

    id: str
    type: Literal["Feature"]
    properties: dict[str, Any] = Field(default_factory=dict)
    geometry: GeoJSONGeometry
    bbox: list[float]
