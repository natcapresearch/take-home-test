import uuid
from typing import TYPE_CHECKING

from pydantic.alias_generators import to_snake
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.backend.app.models.base import BaseModel
from src.backend.app.models.fields import (
    AnalysisYearsField,
    OrganisationConfigField,
)
from src.backend.app.schemas.organisation import (
    AnalysisYears,
    OrganisationConfig,
)

if TYPE_CHECKING:
    from src.backend.app.models.change_set import Change, ChangeSet
    from src.backend.app.models.commodity_location_entity import (
        CommodityLocationEntity,
    )
    from src.backend.app.models.export.exported_commodity_location import (
        ExportedCommodityLocation,
    )


class Organisation(BaseModel):
    policy_resource_type = "org"

    name: Mapped[str] = mapped_column(String, nullable=False)
    authorised_email_domains: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False
    )
    description: Mapped[str] = mapped_column(String, nullable=True)

    config: Mapped[OrganisationConfig | None] = mapped_column(
        OrganisationConfigField,
        nullable=True,
        comment="Holds the configuration and feature flag values for an org.",
    )
    analysis_years: Mapped[AnalysisYears | None] = mapped_column(
        AnalysisYearsField,
        nullable=True,
        doc="Analysis years for the organisation's data",
    )

    # A reference to the default change set for this organisation
    default_change_set_uid: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "change_set.uid", name="fk_organisation_default_change_set_uid"
        ),
        nullable=True,
    )

    # Commodity location relationships
    commodity_location_entities: Mapped[list["CommodityLocationEntity"]] = (
        relationship(
            "CommodityLocationEntity",
            back_populates="organisation",
            cascade="all, delete-orphan",
            passive_deletes=True,
        )
    )
    exported_commodity_locations: Mapped[list["ExportedCommodityLocation"]] = (
        relationship(
            "ExportedCommodityLocation",
            back_populates="organisation",
            cascade="all, delete-orphan",
            passive_deletes=True,
        )
    )

    # Change set relationships
    change_sets: Mapped[list["ChangeSet"]] = relationship(
        "ChangeSet",
        back_populates="organisation",
        foreign_keys="ChangeSet.org_uid",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    changes: Mapped[list["Change"]] = relationship(
        "Change",
        back_populates="organisation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Org:  {self.name}>"


class OrganisationMixin:
    """
    A mixin used by all models that should be associated with an organisation in a many-to-one relation
    """

    policy_resource_type = "org"

    org_uid: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisation.uid", ondelete="CASCADE")
    )

    @declared_attr
    @classmethod
    def organisation(cls) -> Mapped["Organisation"]:
        name = to_snake(cls.__name__).lower()
        if name.endswith("y"):
            name = name[:-1] + "ie"
        elif name.endswith("s"):
            name += "e"
        return relationship(
            "Organisation", back_populates=f"{name}s", foreign_keys=cls.org_uid
        )
