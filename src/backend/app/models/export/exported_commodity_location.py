import uuid
from typing import Any

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column
from src.backend.app.models.base import BaseModel
from src.backend.app.models.organisation import OrganisationMixin


class ExportedCommodityLocation(OrganisationMixin, BaseModel):
    """
    A commodity-location's attributes as of one change set.

    Written per change set (one row per CommodityLocationEntity per change
    set) and resolved by walking `change` records.
    """

    commodity_source_uid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        doc="Legacy pointer to a dropped `commodity_source` table; no FK.",
    )

    entity_uid: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("commodity_location_entity.uid"),
        nullable=True,
        doc="Foreign key to the CommodityLocationEntity this exported commodity location is linked to",
    )

    identifier: Mapped[str] = mapped_column(
        String,
        nullable=False,
        doc="A data platform defined unique identifier for the commodity location",
    )
    commodity_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        doc="The type of commodity (e.g. 'Nuts', 'Cereal Crops')",
    )
    commodity_subgroup: Mapped[str] = mapped_column(
        String,
        nullable=False,
        doc="The subgroup of the commodity (e.g. 'Almonds', 'Barley')",
    )
    commodity_code: Mapped[str] = mapped_column(
        String,
        nullable=False,
        doc="A data platform defined identifier for the commodity",
    )
    year_purchased: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="The year the commodity was purchased from this location",
    )
    sourcing_country_name: Mapped[str] = mapped_column(
        String,
        nullable=True,
        doc="The name of the country where the commodity was sourced",
    )
    sourcing_country_code: Mapped[str] = mapped_column(
        String,
        nullable=True,
        doc="The ISO 3166-1 alpha-2 code of the country where the commodity was sourced",
    )
    sourcing_administrative_level_1_name: Mapped[str] = mapped_column(
        String,
        nullable=True,
        doc="The name of the administrative level 1 region where the commodity was sourced",
    )
    product: Mapped[str] = mapped_column(
        String, nullable=True, doc="The name of the product"
    )
    supplier: Mapped[str] = mapped_column(
        String, nullable=True, doc="The name of the supplier"
    )
    quantity_kilograms: Mapped[float] = mapped_column(
        nullable=True,
        doc="The quantity of the commodity purchased in kilograms",
    )
    spend: Mapped[float] = mapped_column(
        nullable=True, doc="The spend on the commodity"
    )
    group: Mapped[str] = mapped_column(
        String,
        nullable=True,
        doc="The data platform defined commodity group, e.g. Agriculture",
    )
    isic_activity: Mapped[str] = mapped_column(
        String,
        nullable=True,
        doc="The string name (not code) ISIC activity, derived from the commodity",
    )

    __table_args__ = (
        Index(
            "idx_ecl_org_commodity_subgroup",
            "org_uid",
            "commodity_subgroup",
        ),
        Index(
            "idx_ecl_org_commodity_country",
            "org_uid",
            "commodity_subgroup",
            "sourcing_country_code",
        ),
        # Composite so it also serves plain entity_uid lookups. Backs the
        # `ROW_NUMBER() OVER (PARTITION BY entity_uid ORDER BY created_at
        # DESC)` pattern used by the v2 commodity-location endpoints to find
        # the latest row per entity.
        Index(
            "ix_exported_commodity_location_entity_uid_created_at",
            "entity_uid",
            "created_at",
        ),
        Index(
            "ix_ecl_org_sourcing_country_name",
            "org_uid",
            "sourcing_country_name",
        ),
    )

    @declared_attr.directive
    @classmethod
    def __matching_columns__(cls) -> list[Mapped[Any]]:
        # Each edit/upload writes a new, immutable row rather than updating
        # one in place, so `entity_uid` (not `uid`) is this row's identity
        # across changesets — required for change_set_query to resolve the
        # row current as of a given changeset.
        return [cls.entity_uid]
