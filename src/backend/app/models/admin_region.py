from typing import Any

from sqlalchemy import Enum, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.backend.app.models.base import BaseModel
from src.backend.app.util.enums import AdminRegionLevel


class AdminRegion(BaseModel):
    """
    Stores administrative region boundaries at various levels
    (country, region, subregion, etc.) with their GeoJSON geometries.
    """

    policy_resource_type = "common"

    level: Mapped[AdminRegionLevel] = mapped_column(
        Enum(AdminRegionLevel, name="adminregionlevel"),
        nullable=False,
        doc="The administrative level of this region",
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        doc="The name of the region",
    )
    country_code: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
        doc="ISO A2 country code for the country this region belongs to (e.g. 'AF')",
    )
    country_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        doc="The name of the country this region belongs to",
    )

    geojson: Mapped[Any | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="GeoJSON geometry for the region boundary",
    )
    geojson_simplified: Mapped[Any | None] = mapped_column(
        JSONB,
        nullable=True,
        doc=(
            "Douglas-Peucker simplified (tolerance=0.02 deg) GeoJSON geometry, "
            "for low-zoom map backgrounds where full boundary precision is not "
            "needed. Falls back to `geojson` where null."
        ),
    )

    __table_args__ = (
        Index(
            "ix_admin_region_level",
            "level",
            "country_code",
        ),
        Index(
            "ix_admin_region_country_name_name",
            "level",
            "country_name",
            "name",
        ),
        Index(
            "ix_admin_region_country_code_name_level",
            "level",
            "country_code",
            "name",
            unique=True,
        ),
        Index(
            "ix_admin_region_level_name",
            "level",
            "name",
        ),
    )
