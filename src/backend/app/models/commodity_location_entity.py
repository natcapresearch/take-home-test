import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.backend.app.models.base import BaseModel
from src.backend.app.models.organisation import OrganisationMixin


class CommodityLocationEntity(OrganisationMixin, BaseModel):
    policy_resource_type = "common"

    identifier: Mapped[str] = mapped_column(String, nullable=False)
    commodity_type: Mapped[str] = mapped_column(String, nullable=False)
    commodity_subgroup: Mapped[str] = mapped_column(String, nullable=False)
    commodity_code: Mapped[str] = mapped_column(String, nullable=False)
    year_purchased: Mapped[int] = mapped_column(Integer, nullable=False)
    sourcing_admin_region_uid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_region.uid"),
        nullable=True,
        index=True,
    )
    product: Mapped[str | None] = mapped_column(String, nullable=True)
    supplier: Mapped[str | None] = mapped_column(String, nullable=True)
    isic_activity: Mapped[str | None] = mapped_column(String, nullable=True)
    isic_activity_group: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    normalised_key: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        # Composite so it also serves plain org_uid lookups; "identifier" is
        # the default sort_on for the v2 commodity location listing
        # endpoints, so this index supports the ORDER BY without a full
        # in-memory sort.
        Index(
            "ix_commodity_location_entity_org_uid_identifier",
            "org_uid",
            "identifier",
        ),
        UniqueConstraint(
            "org_uid",
            "normalised_key",
            name="uq_commodity_location_entity_org_key",
        ),
    )
