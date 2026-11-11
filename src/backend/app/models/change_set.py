import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.backend.app.models.base import BaseModel
from src.backend.app.models.organisation import OrganisationMixin
from src.backend.app.util.enums import ChangeSetState


class ChangeSet(OrganisationMixin, BaseModel):
    policy_resource_type = "change_set"

    parent_uid: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("change_set.uid"), nullable=True
    )

    state: Mapped[ChangeSetState] = mapped_column(
        Enum(ChangeSetState), nullable=False, default=ChangeSetState.DRAFT
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    unpublished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    datashape: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

    __table_args__ = (
        Index("idx_change_set_org_uid_state", "org_uid", "state"),
    )


class Change(OrganisationMixin, BaseModel):
    change_set_uid: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("change_set.uid"), nullable=False
    )

    model_type: Mapped[str] = mapped_column(String, nullable=False)

    new_uid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    previous_uid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    description: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        Index(
            "idx_change_org_uid_change_set_uid_model_type_incl_new_uid",
            "org_uid",
            "change_set_uid",
            "model_type",
            postgresql_include=["new_uid"],
        ),
        Index("ix_change_new_uid", "new_uid"),
        Index(
            "idx_change_org_uid_model_type_created_at",
            "org_uid",
            "model_type",
            "created_at",
        ),
        Index(
            "idx_change_org_uid_model_type_previous_uid",
            "org_uid",
            "model_type",
            "previous_uid",
        ),
        Index(
            "idx_change_org_uid_model_type_new_uid",
            "org_uid",
            "model_type",
            "new_uid",
        ),
    )
