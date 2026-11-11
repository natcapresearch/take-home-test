-- Minimal DDL for testing scripts/seed.py against a throwaway Postgres.
-- Written from the platform models on origin/main (models/organisation.py,
-- models/change_set.py, models/commodity_location_entity.py,
-- models/export/exported_commodity_location.py, models/admin_region.py,
-- models/base.py) minus the columns the slice drops. The real schema comes
-- from alembic; this file is only a stand-in for that.

CREATE TYPE changesetstate AS ENUM ('DRAFT', 'PROCESSING', 'DONE', 'PUBLISHED');
CREATE TYPE adminregionlevel AS ENUM ('COUNTRY', 'REGION', 'SUBREGION');

CREATE TABLE admin_region (
    uid uuid PRIMARY KEY,
    created_at timestamp NOT NULL,
    updated_at timestamp NOT NULL,
    level adminregionlevel NOT NULL,
    name varchar NOT NULL,
    country_code varchar NOT NULL,
    country_name varchar NOT NULL,
    geojson jsonb,
    geojson_simplified jsonb
);
CREATE INDEX ix_admin_region_country_code ON admin_region (country_code);
CREATE UNIQUE INDEX ix_admin_region_country_code_name_level
    ON admin_region (level, country_code, name);

CREATE TABLE organisation (
    uid uuid PRIMARY KEY,
    created_at timestamp NOT NULL,
    updated_at timestamp NOT NULL,
    name varchar NOT NULL,
    authorised_email_domains varchar[] NOT NULL,
    description varchar,
    config jsonb,
    analysis_years jsonb,
    default_change_set_uid uuid
);

CREATE TABLE change_set (
    uid uuid PRIMARY KEY,
    created_at timestamp NOT NULL,
    updated_at timestamp NOT NULL,
    org_uid uuid NOT NULL REFERENCES organisation (uid) ON DELETE CASCADE,
    parent_uid uuid REFERENCES change_set (uid),
    state changesetstate NOT NULL,
    processed_at timestamp,
    published_at timestamp,
    unpublished_at timestamp,
    name varchar,
    description varchar,
    datashape jsonb
);
CREATE INDEX idx_change_set_org_uid_state ON change_set (org_uid, state);

ALTER TABLE organisation
    ADD CONSTRAINT fk_organisation_default_change_set_uid
    FOREIGN KEY (default_change_set_uid) REFERENCES change_set (uid);

CREATE TABLE change (
    uid uuid PRIMARY KEY,
    created_at timestamp NOT NULL,
    updated_at timestamp NOT NULL,
    org_uid uuid NOT NULL REFERENCES organisation (uid) ON DELETE CASCADE,
    change_set_uid uuid NOT NULL REFERENCES change_set (uid),
    model_type varchar NOT NULL,
    new_uid uuid,
    previous_uid uuid,
    description varchar NOT NULL
);
CREATE INDEX idx_change_org_uid_change_set_uid_model_type_incl_new_uid
    ON change (org_uid, change_set_uid, model_type) INCLUDE (new_uid);
CREATE INDEX ix_change_new_uid ON change (new_uid);

CREATE TABLE commodity_location_entity (
    uid uuid PRIMARY KEY,
    created_at timestamp NOT NULL,
    updated_at timestamp NOT NULL,
    org_uid uuid NOT NULL REFERENCES organisation (uid) ON DELETE CASCADE,
    identifier varchar NOT NULL,
    commodity_type varchar NOT NULL,
    commodity_subgroup varchar NOT NULL,
    commodity_code varchar NOT NULL,
    year_purchased integer NOT NULL,
    sourcing_admin_region_uid uuid REFERENCES admin_region (uid),
    product varchar,
    supplier varchar,
    isic_activity varchar,
    isic_activity_group varchar,
    normalised_key varchar NOT NULL,
    CONSTRAINT uq_commodity_location_entity_org_key UNIQUE (org_uid, normalised_key)
);
CREATE INDEX ix_commodity_location_entity_org_uid_identifier
    ON commodity_location_entity (org_uid, identifier);
CREATE INDEX ix_commodity_location_entity_sourcing_admin_region_uid
    ON commodity_location_entity (sourcing_admin_region_uid);

CREATE TABLE exported_commodity_location (
    uid uuid PRIMARY KEY,
    created_at timestamp NOT NULL,
    updated_at timestamp NOT NULL,
    org_uid uuid NOT NULL REFERENCES organisation (uid) ON DELETE CASCADE,
    commodity_source_uid uuid,
    entity_uid uuid REFERENCES commodity_location_entity (uid),
    identifier varchar NOT NULL,
    commodity_type varchar NOT NULL,
    commodity_subgroup varchar NOT NULL,
    commodity_code varchar NOT NULL,
    year_purchased integer NOT NULL,
    sourcing_country_name varchar,
    sourcing_country_code varchar,
    sourcing_administrative_level_1_name varchar,
    product varchar,
    supplier varchar,
    quantity_kilograms double precision,
    spend double precision,
    "group" varchar,
    isic_activity varchar
);
CREATE INDEX ix_exported_commodity_location_commodity_source_uid
    ON exported_commodity_location (commodity_source_uid);
CREATE INDEX ix_exported_commodity_location_entity_uid_created_at
    ON exported_commodity_location (entity_uid, created_at);
