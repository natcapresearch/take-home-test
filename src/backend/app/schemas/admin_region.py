from typing import Any

from pydantic import UUID4
from src.backend.app.schemas.base import BasePlainSchema
from src.backend.app.util.enums import AdminRegionLevel


class AdminRegionBrief(BasePlainSchema):
    """Lightweight response without geojson geometry."""

    uid: UUID4
    level: AdminRegionLevel
    name: str
    country_code: str
    country_name: str


class AdminRegionRead(BasePlainSchema):
    """Full response including geojson geometry."""

    uid: UUID4
    level: AdminRegionLevel
    name: str
    country_code: str
    country_name: str
    geojson: Any | None = None
