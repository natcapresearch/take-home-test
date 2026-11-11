"""initial schema

Revision ID: 8089b785c901
Revises:
Create Date: 2026-11-10 22:17:29.407903

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8089b785c901"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_region",
        sa.Column(
            "level",
            sa.Enum("COUNTRY", "REGION", "SUBREGION", name="adminregionlevel"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("country_code", sa.String(), nullable=False),
        sa.Column("country_name", sa.String(), nullable=False),
        sa.Column(
            "geojson", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "geojson_simplified",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("uid", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        op.f("ix_admin_region_country_code"),
        "admin_region",
        ["country_code"],
        unique=False,
    )
    op.create_index(
        "ix_admin_region_country_code_name_level",
        "admin_region",
        ["level", "country_code", "name"],
        unique=True,
    )
    op.create_index(
        "ix_admin_region_country_name_name",
        "admin_region",
        ["level", "country_name", "name"],
        unique=False,
    )
    op.create_index(
        "ix_admin_region_level",
        "admin_region",
        ["level", "country_code"],
        unique=False,
    )
    op.create_index(
        "ix_admin_region_level_name",
        "admin_region",
        ["level", "name"],
        unique=False,
    )
    op.create_table(
        "organisation",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "authorised_email_domains",
            postgresql.ARRAY(sa.String()),
            nullable=False,
        ),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Holds the configuration and feature flag values for an org.",
        ),
        sa.Column(
            "analysis_years",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("default_change_set_uid", sa.UUID(), nullable=True),
        sa.Column("uid", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_table(
        "change_set",
        sa.Column("parent_uid", sa.UUID(), nullable=True),
        sa.Column(
            "state",
            sa.Enum(
                "DRAFT",
                "PROCESSING",
                "DONE",
                "PUBLISHED",
                name="changesetstate",
            ),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("unpublished_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "datashape", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("org_uid", sa.UUID(), nullable=False),
        sa.Column("uid", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_uid"], ["organisation.uid"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["parent_uid"],
            ["change_set.uid"],
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "idx_change_set_org_uid_state",
        "change_set",
        ["org_uid", "state"],
        unique=False,
    )
    # organisation and change_set reference each other, so the organisation
    # table is created first and this constraint added once both exist.
    op.create_foreign_key(
        "fk_organisation_default_change_set_uid",
        "organisation",
        "change_set",
        ["default_change_set_uid"],
        ["uid"],
    )
    op.create_table(
        "change",
        sa.Column("change_set_uid", sa.UUID(), nullable=False),
        sa.Column("model_type", sa.String(), nullable=False),
        sa.Column("new_uid", sa.UUID(), nullable=True),
        sa.Column("previous_uid", sa.UUID(), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("org_uid", sa.UUID(), nullable=False),
        sa.Column("uid", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["change_set_uid"],
            ["change_set.uid"],
        ),
        sa.ForeignKeyConstraint(
            ["org_uid"], ["organisation.uid"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "idx_change_org_uid_change_set_uid_model_type_incl_new_uid",
        "change",
        ["org_uid", "change_set_uid", "model_type"],
        unique=False,
        postgresql_include=["new_uid"],
    )
    op.create_index(
        "idx_change_org_uid_model_type_created_at",
        "change",
        ["org_uid", "model_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_change_org_uid_model_type_new_uid",
        "change",
        ["org_uid", "model_type", "new_uid"],
        unique=False,
    )
    op.create_index(
        "idx_change_org_uid_model_type_previous_uid",
        "change",
        ["org_uid", "model_type", "previous_uid"],
        unique=False,
    )
    op.create_index("ix_change_new_uid", "change", ["new_uid"], unique=False)
    op.create_table(
        "commodity_location_entity",
        sa.Column("identifier", sa.String(), nullable=False),
        sa.Column("commodity_type", sa.String(), nullable=False),
        sa.Column("commodity_subgroup", sa.String(), nullable=False),
        sa.Column("commodity_code", sa.String(), nullable=False),
        sa.Column("year_purchased", sa.Integer(), nullable=False),
        sa.Column("sourcing_admin_region_uid", sa.UUID(), nullable=True),
        sa.Column("product", sa.String(), nullable=True),
        sa.Column("supplier", sa.String(), nullable=True),
        sa.Column("isic_activity", sa.String(), nullable=True),
        sa.Column("isic_activity_group", sa.String(), nullable=True),
        sa.Column("normalised_key", sa.String(), nullable=False),
        sa.Column("org_uid", sa.UUID(), nullable=False),
        sa.Column("uid", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_uid"], ["organisation.uid"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sourcing_admin_region_uid"],
            ["admin_region.uid"],
        ),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint(
            "org_uid",
            "normalised_key",
            name="uq_commodity_location_entity_org_key",
        ),
    )
    op.create_index(
        "ix_commodity_location_entity_org_uid_identifier",
        "commodity_location_entity",
        ["org_uid", "identifier"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commodity_location_entity_sourcing_admin_region_uid"),
        "commodity_location_entity",
        ["sourcing_admin_region_uid"],
        unique=False,
    )
    op.create_table(
        "exported_commodity_location",
        sa.Column("commodity_source_uid", sa.UUID(), nullable=True),
        sa.Column("entity_uid", sa.UUID(), nullable=True),
        sa.Column("identifier", sa.String(), nullable=False),
        sa.Column("commodity_type", sa.String(), nullable=False),
        sa.Column("commodity_subgroup", sa.String(), nullable=False),
        sa.Column("commodity_code", sa.String(), nullable=False),
        sa.Column("year_purchased", sa.Integer(), nullable=False),
        sa.Column("sourcing_country_name", sa.String(), nullable=True),
        sa.Column("sourcing_country_code", sa.String(), nullable=True),
        sa.Column(
            "sourcing_administrative_level_1_name", sa.String(), nullable=True
        ),
        sa.Column("product", sa.String(), nullable=True),
        sa.Column("supplier", sa.String(), nullable=True),
        sa.Column("quantity_kilograms", sa.Float(), nullable=True),
        sa.Column("spend", sa.Float(), nullable=True),
        sa.Column("group", sa.String(), nullable=True),
        sa.Column("isic_activity", sa.String(), nullable=True),
        sa.Column("org_uid", sa.UUID(), nullable=False),
        sa.Column("uid", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_uid"],
            ["commodity_location_entity.uid"],
        ),
        sa.ForeignKeyConstraint(
            ["org_uid"], ["organisation.uid"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "idx_ecl_org_commodity_country",
        "exported_commodity_location",
        ["org_uid", "commodity_subgroup", "sourcing_country_code"],
        unique=False,
    )
    op.create_index(
        "idx_ecl_org_commodity_subgroup",
        "exported_commodity_location",
        ["org_uid", "commodity_subgroup"],
        unique=False,
    )
    op.create_index(
        "ix_ecl_org_sourcing_country_name",
        "exported_commodity_location",
        ["org_uid", "sourcing_country_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exported_commodity_location_commodity_source_uid"),
        "exported_commodity_location",
        ["commodity_source_uid"],
        unique=False,
    )
    op.create_index(
        "ix_exported_commodity_location_entity_uid_created_at",
        "exported_commodity_location",
        ["entity_uid", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_organisation_default_change_set_uid",
        "organisation",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_exported_commodity_location_entity_uid_created_at",
        table_name="exported_commodity_location",
    )
    op.drop_index(
        op.f("ix_exported_commodity_location_commodity_source_uid"),
        table_name="exported_commodity_location",
    )
    op.drop_index(
        "ix_ecl_org_sourcing_country_name",
        table_name="exported_commodity_location",
    )
    op.drop_index(
        "idx_ecl_org_commodity_subgroup",
        table_name="exported_commodity_location",
    )
    op.drop_index(
        "idx_ecl_org_commodity_country",
        table_name="exported_commodity_location",
    )
    op.drop_table("exported_commodity_location")
    op.drop_index(
        op.f("ix_commodity_location_entity_sourcing_admin_region_uid"),
        table_name="commodity_location_entity",
    )
    op.drop_index(
        "ix_commodity_location_entity_org_uid_identifier",
        table_name="commodity_location_entity",
    )
    op.drop_table("commodity_location_entity")
    op.drop_index("ix_change_new_uid", table_name="change")
    op.drop_index(
        "idx_change_org_uid_model_type_previous_uid", table_name="change"
    )
    op.drop_index("idx_change_org_uid_model_type_new_uid", table_name="change")
    op.drop_index(
        "idx_change_org_uid_model_type_created_at", table_name="change"
    )
    op.drop_index(
        "idx_change_org_uid_change_set_uid_model_type_incl_new_uid",
        table_name="change",
        postgresql_include=["new_uid"],
    )
    op.drop_table("change")
    op.drop_index("idx_change_set_org_uid_state", table_name="change_set")
    op.drop_table("change_set")
    op.drop_table("organisation")
    op.drop_index("ix_admin_region_level_name", table_name="admin_region")
    op.drop_index("ix_admin_region_level", table_name="admin_region")
    op.drop_index(
        "ix_admin_region_country_name_name", table_name="admin_region"
    )
    op.drop_index(
        "ix_admin_region_country_code_name_level", table_name="admin_region"
    )
    op.drop_index(
        op.f("ix_admin_region_country_code"), table_name="admin_region"
    )
    op.drop_table("admin_region")
