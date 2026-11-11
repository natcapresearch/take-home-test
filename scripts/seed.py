#!/usr/bin/env python3
"""Seed the take-home slice database with one organisation and two versions.

Standalone: talks to Postgres through psycopg2 with explicit SQL and table
names, so it keeps working while the ORM models in src/backend are trimmed.

What it creates (all deterministic, so the dump is stable between runs):

  organisation               1 row   "Example Foods Ltd"
  admin_region               from scripts/data/admin_regions.json (upserted,
                             shared between orgs, never deleted by --reset)
  commodity_location_entity  120 rows in Version 1, +3 in Version 2
  exported_commodity_location one row per entity per version it was written in
  change_set                 "Version 1" (published) and "Version 2" (done)
  change                     the creation / tombstone records that make the
                             versioned reads resolve the rows above

How the versioned reads resolve rows (src/backend/app/util/change_set.py
`change_set_query`): walk the change_set parent chain from the requested
change set up, collect every `change` row with model_type = <tablename>, join
each to the model row at COALESCE(new_uid, previous_uid), and per entity keep
the row from the nearest change set whose change says "created" (new_uid =
row uid) and that has the latest created_at. A change with new_uid NULL and
previous_uid = <row> is a tombstone: the row is dead from that change set on.

Connection: DATABASE_URL, or DB_HOST / DB_PORT / DB_USERNAME / DB_PASSWORD /
DB_NAME (defaults: localhost / 5432 / postgres / postgres / postgres).

Usage:
    poetry run python scripts/seed.py            # refuses if the org exists
    poetry run python scripts/seed.py --reset    # deletes the org's rows first
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import psycopg2
import psycopg2.extras

psycopg2.extras.register_uuid()

# --------------------------------------------------------------------------
# Fixed identities. uuid5 from one namespace so they can be quoted in docs.
# --------------------------------------------------------------------------

NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "take-home-test.seed.example")


def stable_uid(*parts: str) -> uuid.UUID:
    """Deterministic uid derived from `parts`, shaped as a version-4 UUID.

    The backend validates every uid it receives as UUIDv4, so a plain uuid5
    would be rejected; keep uuid5's determinism but set the v4 version and
    RFC 4122 variant bits.
    """
    derived = uuid.uuid5(NAMESPACE, "/".join(parts)).int
    derived &= ~(0xF << 76)  # clear version nibble
    derived |= 0x4 << 76  # version 4
    derived &= ~(0x3 << 62)  # clear variant bits
    derived |= 0x2 << 62  # RFC 4122 variant
    return uuid.UUID(int=derived)


ORG_UID = stable_uid("organisation", "example-foods")
ORG_NAME = "Example Foods Ltd"
V1_UID = stable_uid("change_set", "version-1")
V2_UID = stable_uid("change_set", "version-2")

# Fixed timestamps. Rows in Version 2 must be created later than the Version
# 1 rows they replace: change_set_query breaks ties per entity on created_at.
T_BASE = datetime(2026, 1, 15, 9, 0, 0)
T_V1 = datetime(2026, 1, 15, 10, 0, 0)
T_V1_PUBLISHED = datetime(2026, 1, 16, 9, 0, 0)
T_V2 = datetime(2026, 3, 2, 10, 0, 0)

# `change.model_type` is the SQLAlchemy __tablename__ of the model the change
# is about (util/change_set.py `create_change`, line 290). The descriptions
# are the literal strings the export loader writes
# (util/export_change_recorder.py lines 478, 564, 577).
MODEL_ENTITY = "commodity_location_entity"
MODEL_EXPORTED = "exported_commodity_location"
DESC_ENTITY_CREATED = "Created CommodityLocationEntity record"
DESC_ENTITY_REMOVED = "Removed CommodityLocationEntity record"
DESC_EXPORTED_LOADED = "Loaded ExportedCommodityLocation record"
DESC_EXPORTED_REMOVED = "Removed ExportedCommodityLocation record"

ADMIN_REGIONS_FILE = Path(__file__).parent / "data" / "admin_regions.json"

# --------------------------------------------------------------------------
# Reference data. Commodity codes / types / subgroups / group / ISIC activity
# are the platform's own entries from
# src/backend/app/schemas/data_template_target_model/commodities.py.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Commodity:
    code: str
    type: str
    subgroup: str
    group: str
    isic_activity: str
    countries: tuple[str, ...]
    suppliers: tuple[str, ...]
    products: tuple[str, ...]
    kg_range: tuple[int, int]
    usd_per_kg: float


ISIC_NON_PERENNIAL_CEREALS = (
    "Agriculture, forestry and fishing / Crop and animal production, hunting "
    "and related service activities / Growing of non-perennial crops / "
    "Growing of cereals (except rice), leguminous crops and oil seeds"
)
ISIC_BEVERAGE = (
    "Agriculture, forestry and fishing / Crop and animal production, hunting "
    "and related service activities / Growing of perennial crops / "
    "Growing of beverage crops"
)

COMMODITIES: list[Commodity] = [
    Commodity(
        "CFAG", "Beverage crops and cocoa", "Coffee - arabica (green)",
        "Agriculture", ISIC_BEVERAGE,
        ("BR", "CO", "VN", "ET"),
        ("Andes Coffee Cooperative", "Minas Verde Exports", "Highland Beans Co"),
        ("Roast & ground coffee", "Instant coffee", "Espresso capsules"),
        (40_000, 1_500_000), 4.2,
    ),
    Commodity(
        "COC", "Beverage crops and cocoa", "Cocoa (dried beans)",
        "Agriculture", ISIC_BEVERAGE,
        ("CI", "GH", "ID", "BR"),
        ("Golden Pod Traders", "Abidjan Cocoa SA", "Sulawesi Beans Ltd"),
        ("Chocolate bars", "Cocoa powder", "Baking chocolate"),
        (50_000, 2_000_000), 3.1,
    ),
    Commodity(
        "PLMO", "Oilseeds and oleaginous fruits", "Palm (crude oil)",
        "Agriculture",
        "Agriculture, forestry and fishing / Crop and animal production, "
        "hunting and related service activities / Growing of perennial crops "
        "/ Growing of oleaginous fruits",
        ("ID", "MY", "TH", "CO"),
        ("Borneo Palm Mills", "Peninsular Oils Sdn Bhd", "Tropic Refiners"),
        ("Margarine", "Frying oil", "Snack coatings"),
        (100_000, 4_000_000), 0.95,
    ),
    Commodity(
        "SYBB", "Beans and legumes", "Soybean (beans)",
        "Agriculture", ISIC_NON_PERENNIAL_CEREALS,
        ("BR", "US", "AR"),
        ("Cerrado Grains SA", "Midwest Soy Partners", "Pampa Agro Exports"),
        ("Soy protein", "Animal feed", "Soy milk"),
        (200_000, 6_000_000), 0.55,
    ),
    Commodity(
        "SCNS", "Sugar crops", "Sugar cane (sugar)",
        "Agriculture",
        "Agriculture, forestry and fishing / Crop and animal production, "
        "hunting and related service activities / Growing of non-perennial "
        "crops / Growing of sugar cane",
        ("BR", "IN", "TH", "AU"),
        ("Usina Doce Ltda", "Maharashtra Sugar Mills", "Queensland Cane Co"),
        ("Granulated sugar", "Syrups", "Confectionery"),
        (150_000, 5_000_000), 0.48,
    ),
    Commodity(
        "WHT", "Cereal crops", "Wheat",
        "Agriculture", ISIC_NON_PERENNIAL_CEREALS,
        ("US", "FR", "UA", "AU", "AR"),
        ("Plains Grain Elevators", "Beauce Cereales", "Black Sea Grain Hub"),
        ("Flour", "Bread", "Pasta"),
        (300_000, 8_000_000), 0.32,
    ),
    Commodity(
        "MAZ", "Cereal crops", "Maize (corn)",
        "Agriculture", ISIC_NON_PERENNIAL_CEREALS,
        ("US", "BR", "AR", "UA"),
        ("Corn Belt Supply", "Mato Grosso Grains", "Dnipro Agro"),
        ("Corn flakes", "Corn starch", "Tortilla chips"),
        (250_000, 7_000_000), 0.27,
    ),
    Commodity(
        "RCE", "Cereal crops", "Rice",
        "Agriculture",
        "Agriculture, forestry and fishing / Crop and animal production, "
        "hunting and related service activities / Growing of non-perennial "
        "crops / Growing of rice",
        ("IN", "VN", "TH", "ID"),
        ("Mekong Delta Rice", "Punjab Basmati Exports", "Siam Rice Trading"),
        ("Long grain rice", "Rice noodles", "Rice crackers"),
        (100_000, 3_500_000), 0.62,
    ),
    Commodity(
        "CTNF", "Fibre crops and materials", "Cotton (fibre)",
        "Agriculture",
        "Agriculture, forestry and fishing / Crop and animal production, "
        "hunting and related service activities / Growing of non-perennial "
        "crops / Growing of fibre crops",
        ("US", "IN", "BR", "AU"),
        ("Delta Cotton Gins", "Gujarat Fibre Mills", "Bahia Cotton SA"),
        ("Packaging textiles", "Uniforms", "Tote bags"),
        (20_000, 800_000), 2.1,
    ),
    Commodity(
        "NRB", "Plastics and rubber", "Natural rubber",
        "Agriculture",
        "Agriculture, forestry and fishing / Crop and animal production, "
        "hunting and related service activities / Growing of perennial crops "
        "/ Growing of other perennial crops",
        ("TH", "ID", "VN", "MY"),
        ("Rayong Latex Co", "Sumatra Rubber Estates", "Tay Nguyen Rubber"),
        ("Conveyor belts", "Seals and gaskets", "Gloves"),
        (10_000, 600_000), 1.7,
    ),
    Commodity(
        "CMTC", "Meat", "Cattle meat (carcass weight)",
        "Animal",
        "Agriculture, forestry and fishing / Crop and animal production, "
        "hunting and related service activities / Animal production / "
        "Raising of cattle and buffaloes",
        ("BR", "AU", "US", "AR"),
        ("Frigorifico Sul", "Outback Beef Exports", "Prairie Meats Inc"),
        ("Ready meals", "Beef jerky", "Canned beef"),
        (15_000, 900_000), 5.4,
    ),
    Commodity(
        "TMBSPT", "Timber and forest products", "Softwood (timber)",
        "Silviculture",
        "Agriculture, forestry and fishing / Forestry and logging / Logging "
        "/ Logging",
        ("US", "BR", "AU", "FR"),
        ("Cascadia Sawmills", "Parana Pine Ltd", "Landes Forestry SA"),
        ("Pallets", "Crates", "Shelving"),
        (50_000, 2_500_000), 0.21,
    ),
]

# ISO 3166-1 alpha-2 codes, the format of both exported_commodity_location.
# sourcing_country_code (model doc) and admin_region.country_code (loaded
# from Natural Earth `iso_a2` by workers/load_admin_regions/main.py).
# The name is used only when scripts/data/admin_regions.json has no COUNTRY
# row for the code; otherwise that row's country_name wins, so the exported
# row names match the admin_region names the map joins on.
COUNTRY_NAMES: dict[str, str] = {
    "AR": "Argentina",
    "AU": "Australia",
    "BR": "Brazil",
    "CI": "Côte d'Ivoire",
    "CO": "Colombia",
    "ET": "Ethiopia",
    "FR": "France",
    "GH": "Ghana",
    "ID": "Indonesia",
    "IN": "India",
    "MY": "Malaysia",
    "TH": "Thailand",
    "UA": "Ukraine",
    "US": "United States of America",
    "VN": "Vietnam",
}

ROWS_PER_COMMODITY = 10  # 12 commodities -> 120 rows in Version 1
V2_REPLACED = 10
V2_TOMBSTONED = 2
V2_NEW = 3
NULL_SHARE = 0.10  # share of rows with no quantity, and (independently) no spend


# --------------------------------------------------------------------------
# Data model for the rows we are going to insert.
# --------------------------------------------------------------------------


@dataclass
class AdminRegion:
    uid: uuid.UUID
    level: str  # COUNTRY | REGION
    name: str
    country_code: str
    country_name: str
    geojson_simplified: Any


@dataclass
class Entity:
    uid: uuid.UUID
    identifier: str
    commodity: Commodity
    year_purchased: int
    product: str
    supplier: str
    country_code: str
    country_name: str
    admin_region: AdminRegion | None  # REGION or COUNTRY row, if known
    created_at: datetime

    @property
    def admin_1_name(self) -> str | None:
        if self.admin_region is not None and self.admin_region.level == "REGION":
            return self.admin_region.name
        return None

    @property
    def normalised_key(self) -> str:
        # api/v1/triggers.py `commodity_normalised_key`: the entity's identity
        # within an org (identifier alone is not unique).
        ar = self.admin_region
        sourcing_part = (
            f"{ar.country_code.lower()}-||-{ar.name.lower()}" if ar else ""
        )
        c = self.commodity
        return (
            f"{self.identifier.strip().lower()}-||-"
            f"{c.type.strip().lower()}-||-"
            f"{c.subgroup.strip().lower()}-||-"
            f"{c.code.strip().lower()}-||-"
            f"{self.year_purchased}-||-"
            f"{sourcing_part}-||-"
            f"{self.product.strip().lower()}-||-"
            f"{self.supplier.strip().lower()}"
        )


@dataclass
class ExportedRow:
    uid: uuid.UUID
    entity: Entity
    country_code: str
    country_name: str
    admin_1_name: str | None
    supplier: str
    product: str
    quantity_kilograms: float | None
    spend: float | None
    created_at: datetime


@dataclass
class Change:
    uid: uuid.UUID
    change_set_uid: uuid.UUID
    model_type: str
    new_uid: uuid.UUID | None
    previous_uid: uuid.UUID | None
    description: str
    created_at: datetime


@dataclass
class Seed:
    admin_regions: list[AdminRegion]
    entities: list[Entity] = field(default_factory=list)
    exported: list[ExportedRow] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    # entity uid -> exported row current in each version (None = not alive)
    v1_rows: dict[uuid.UUID, ExportedRow] = field(default_factory=dict)
    v2_rows: dict[uuid.UUID, ExportedRow] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Admin regions
# --------------------------------------------------------------------------


def load_admin_regions(path: Path) -> list[AdminRegion]:
    """scripts/data/admin_regions.json: a JSON array of objects with keys
    uid, name, level (COUNTRY | REGION), country_code (ISO2), country_name,
    geojson_simplified (a GeoJSON geometry, may be null)."""
    with path.open() as f:
        raw = json.load(f)
    regions: list[AdminRegion] = []
    for item in raw:
        level = str(item["level"]).upper()
        if level not in {"COUNTRY", "REGION"}:
            raise ValueError(f"admin region {item.get('uid')}: bad level {level!r}")
        regions.append(
            AdminRegion(
                uid=uuid.UUID(str(item["uid"])),
                level=level,
                name=item["name"],
                country_code=item["country_code"],
                country_name=item["country_name"],
                geojson_simplified=item.get("geojson_simplified"),
            )
        )
    return regions


# --------------------------------------------------------------------------
# Build the seed in memory
# --------------------------------------------------------------------------


def build_seed(admin_regions: list[AdminRegion], rng: random.Random) -> Seed:
    seed = Seed(admin_regions=admin_regions)
    country_rows = {r.country_code: r for r in admin_regions if r.level == "COUNTRY"}
    region_rows: dict[str, list[AdminRegion]] = {}
    for r in admin_regions:
        if r.level == "REGION":
            region_rows.setdefault(r.country_code, []).append(r)
    for rows in region_rows.values():
        rows.sort(key=lambda r: r.name)

    def country_name(code: str) -> str:
        if code in country_rows:
            return country_rows[code].country_name
        return COUNTRY_NAMES[code]

    def pick_region(code: str) -> AdminRegion | None:
        regions = region_rows.get(code)
        if regions and rng.random() < 0.4:
            return rng.choice(regions)
        return country_rows.get(code)

    def amounts(c: Commodity) -> tuple[float | None, float | None]:
        kg = float(rng.randint(*c.kg_range))
        kg = round(kg / 100) * 100
        spend = round(kg * c.usd_per_kg * rng.uniform(0.85, 1.2), 2)
        if rng.random() < NULL_SHARE:
            kg_out: float | None = None
        else:
            kg_out = kg
        spend_out: float | None = None if rng.random() < NULL_SHARE else spend
        return kg_out, spend_out

    def make_entity(index: int, c: Commodity, created_at: datetime) -> Entity:
        code = rng.choice(c.countries)
        return Entity(
            uid=stable_uid("commodity_location_entity", f"COMMOD_{index:03d}"),
            identifier=f"COMMOD_{index:03d}",
            commodity=c,
            year_purchased=rng.choice((2022, 2023, 2024, 2024)),
            product=rng.choice(c.products),
            supplier=rng.choice(c.suppliers),
            country_code=code,
            country_name=country_name(code),
            admin_region=pick_region(code),
            created_at=created_at,
        )

    def make_exported(
        entity: Entity, version: str, created_at: datetime, **overrides: Any
    ) -> ExportedRow:
        kg, spend = amounts(entity.commodity)
        row = ExportedRow(
            uid=stable_uid("exported_commodity_location", version, entity.identifier),
            entity=entity,
            country_code=entity.country_code,
            country_name=entity.country_name,
            admin_1_name=entity.admin_1_name,
            supplier=entity.supplier,
            product=entity.product,
            quantity_kilograms=kg,
            spend=spend,
            created_at=created_at,
        )
        for k, v in overrides.items():
            setattr(row, k, v)
        return row

    def creation(cs: uuid.UUID, model: str, row_uid: uuid.UUID, desc: str, at: datetime) -> Change:
        return Change(
            uid=stable_uid("change", str(cs), model, "created", str(row_uid)),
            change_set_uid=cs, model_type=model, new_uid=row_uid,
            previous_uid=None, description=desc, created_at=at,
        )

    def tombstone(cs: uuid.UUID, model: str, row_uid: uuid.UUID, desc: str, at: datetime) -> Change:
        return Change(
            uid=stable_uid("change", str(cs), model, "removed", str(row_uid)),
            change_set_uid=cs, model_type=model, new_uid=None,
            previous_uid=row_uid, description=desc, created_at=at,
        )

    # ---- Version 1: 120 entities, one exported row each, all created ----
    index = 0
    for c in COMMODITIES:
        for _ in range(ROWS_PER_COMMODITY):
            index += 1
            entity = make_entity(index, c, T_V1)
            row = make_exported(entity, "v1", T_V1)
            seed.entities.append(entity)
            seed.exported.append(row)
            seed.v1_rows[entity.uid] = row
            seed.changes.append(creation(V1_UID, MODEL_ENTITY, entity.uid, DESC_ENTITY_CREATED, T_V1))
            seed.changes.append(creation(V1_UID, MODEL_EXPORTED, row.uid, DESC_EXPORTED_LOADED, T_V1))

    # ---- Version 2: 10 replaced, 2 tombstoned, 3 new ----
    seed.v2_rows = dict(seed.v1_rows)
    v1_entities = list(seed.entities)
    touched = rng.sample(v1_entities, V2_REPLACED + V2_TOMBSTONED)
    replaced, tombstoned = touched[:V2_REPLACED], touched[V2_REPLACED:]

    for entity in replaced:
        old = seed.v1_rows[entity.uid]
        # A replaced row keeps its country and supplier (those are part of the
        # entity's identity; changing them would create a new entity) and only
        # gets new amounts, which make_exported draws.
        new = make_exported(entity, "v2", T_V2)
        # Never let a replacement silently drop a value the old row had, so
        # the diff between versions is about changed numbers, not gaps.
        if new.quantity_kilograms is None and old.quantity_kilograms is not None:
            new.quantity_kilograms = round(old.quantity_kilograms * 1.1 / 100) * 100
        if new.spend is None and old.spend is not None:
            new.spend = round(old.spend * 1.08, 2)
        seed.exported.append(new)
        seed.v2_rows[entity.uid] = new
        # A replacement is recorded as a plain creation of the new row; the
        # versioning query resolves the current row per entity by change set
        # and created_at, so previous_uid is not needed.
        seed.changes.append(creation(V2_UID, MODEL_EXPORTED, new.uid, DESC_EXPORTED_LOADED, T_V2))

    for entity in tombstoned:
        old = seed.v1_rows[entity.uid]
        del seed.v2_rows[entity.uid]
        seed.changes.append(tombstone(V2_UID, MODEL_ENTITY, entity.uid, DESC_ENTITY_REMOVED, T_V2))
        seed.changes.append(tombstone(V2_UID, MODEL_EXPORTED, old.uid, DESC_EXPORTED_REMOVED, T_V2))

    for _ in range(V2_NEW):
        index += 1
        c = rng.choice(COMMODITIES)
        entity = make_entity(index, c, T_V2)
        row = make_exported(entity, "v2", T_V2)
        seed.entities.append(entity)
        seed.exported.append(row)
        seed.v2_rows[entity.uid] = row
        seed.changes.append(creation(V2_UID, MODEL_ENTITY, entity.uid, DESC_ENTITY_CREATED, T_V2))
        seed.changes.append(creation(V2_UID, MODEL_EXPORTED, row.uid, DESC_EXPORTED_LOADED, T_V2))

    return seed


# --------------------------------------------------------------------------
# change_set.datashape and .description
# --------------------------------------------------------------------------


def datashape(rows: dict[uuid.UUID, ExportedRow]) -> dict[str, Any]:
    """`ChangeSetDataShape` (src/backend/app/schemas/change_set.py) dumped
    by_alias, as `refresh_change_set_datashape` in
    src/backend/app/util/change_set.py stores it: counts over the entities
    alive as of the change set, read from each one's exported row current as
    of it."""
    count = len(rows)
    with_spend = sum(1 for r in rows.values() if r.spend is not None)
    return {
        "commodityLocationCount": count,
        "commodityLocationsWithSpendCount": with_spend,
        "fullCommoditySpendCoverage": count > 0 and with_spend == count,
    }


def _coverage(with_value: int, total: int) -> str:
    if with_value == total:
        return "full"
    if with_value == 0:
        return "missing"
    return "partial"


def description(seed: Seed, cs_uid: uuid.UUID) -> str | None:
    """`exported_rows_description` in src/backend/app/api/v1/change_set.py:
    counts the exported rows this change set alone points at through
    change.new_uid - ancestors are not looked at - and reports quantity /
    spend coverage."""
    new_uids = {
        c.new_uid for c in seed.changes
        if c.change_set_uid == cs_uid and c.model_type == MODEL_EXPORTED and c.new_uid
    }
    rows = [r for r in seed.exported if r.uid in new_uids]
    n = len(rows)
    if n == 0:
        return None
    with_qty = sum(1 for r in rows if r.quantity_kilograms is not None)
    with_spend = sum(1 for r in rows if r.spend is not None)
    word = "commodity source" if n == 1 else "commodity sources"
    return ". ".join(
        [
            f"{n} {word}",
            f"Commodity quantity: {_coverage(with_qty, n)}",
            f"Commodity spend: {_coverage(with_spend, n)}",
        ]
    )


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

TABLES = (
    "organisation", "admin_region", "change_set", "change",
    "commodity_location_entity", "exported_commodity_location",
)


def connect() -> psycopg2.extensions.connection:
    url = os.environ.get("DATABASE_URL")
    if url:
        u = urlparse(url)
        return psycopg2.connect(
            host=u.hostname, port=u.port or 5432,
            user=unquote(u.username) if u.username else None,
            password=unquote(u.password) if u.password else None,
            dbname=(u.path or "/postgres").lstrip("/") or "postgres",
        )
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        user=os.environ.get("DB_USERNAME", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
        dbname=os.environ.get("DB_NAME", "postgres"),
    )


def check_schema(cur: Any) -> None:
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = current_schema() AND table_name = ANY(%s)",
        (list(TABLES),),
    )
    present = {r[0] for r in cur.fetchall()}
    missing = [t for t in TABLES if t not in present]
    if missing:
        sys.exit(
            f"Missing tables: {', '.join(missing)}. Create the schema first "
            "(alembic upgrade head)."
        )


def enum_label(cur: Any, type_name: str, wanted: str) -> str:
    """The label of `type_name` that matches `wanted` ignoring case. The
    platform's migrations create changesetstate / adminregionlevel with the
    Python enum *names* (PUBLISHED, COUNTRY), not the values."""
    cur.execute(
        "SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
        "WHERE t.typname = %s",
        (type_name,),
    )
    labels = [r[0] for r in cur.fetchall()]
    if not labels:
        # Column is plain text in this schema; the Python enum name is what
        # SQLAlchemy's Enum type would have written.
        return wanted
    for label in labels:
        if label.lower() == wanted.lower():
            return label
    sys.exit(f"enum {type_name} has no label like {wanted!r}: {labels}")


def reset_org(cur: Any) -> None:
    cur.execute("DELETE FROM change WHERE org_uid = %s", (ORG_UID,))
    cur.execute(
        "UPDATE organisation SET default_change_set_uid = NULL WHERE uid = %s",
        (ORG_UID,),
    )
    # change_set.parent_uid is a self-FK: delete leaves first until none left.
    while True:
        cur.execute(
            "DELETE FROM change_set WHERE org_uid = %s AND uid NOT IN "
            "(SELECT parent_uid FROM change_set WHERE org_uid = %s AND parent_uid IS NOT NULL)",
            (ORG_UID, ORG_UID),
        )
        if cur.rowcount == 0:
            break
    cur.execute("DELETE FROM exported_commodity_location WHERE org_uid = %s", (ORG_UID,))
    cur.execute("DELETE FROM commodity_location_entity WHERE org_uid = %s", (ORG_UID,))
    cur.execute("DELETE FROM organisation WHERE uid = %s", (ORG_UID,))


def upsert_admin_regions(cur: Any, regions: list[AdminRegion], level_labels: dict[str, str]) -> None:
    """admin_region is shared reference data with a unique (level,
    country_code, name) index; match on that first, then on uid, and insert
    otherwise - so the file's uids are kept when the table is empty and an
    existing table is left as it is."""
    for r in regions:
        level = level_labels[r.level]
        cur.execute(
            "SELECT uid FROM admin_region WHERE level = %s AND country_code = %s AND name = %s",
            (level, r.country_code, r.name),
        )
        hit = cur.fetchone()
        if hit is None:
            cur.execute("SELECT uid FROM admin_region WHERE uid = %s", (r.uid,))
            hit = cur.fetchone()
        if hit is not None:
            r.uid = hit[0]
            cur.execute(
                "UPDATE admin_region SET country_name = %s, geojson_simplified = %s, "
                "updated_at = %s WHERE uid = %s",
                (r.country_name, psycopg2.extras.Json(r.geojson_simplified), T_BASE, r.uid),
            )
        else:
            cur.execute(
                "INSERT INTO admin_region (uid, created_at, updated_at, level, name, "
                "country_code, country_name, geojson, geojson_simplified) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s)",
                (
                    r.uid, T_BASE, T_BASE, level, r.name, r.country_code,
                    r.country_name, psycopg2.extras.Json(r.geojson_simplified),
                ),
            )


def insert_seed(cur: Any, seed: Seed, state_labels: dict[str, str]) -> None:
    cur.execute(
        "INSERT INTO organisation (uid, created_at, updated_at, name, "
        "authorised_email_domains, description, config, analysis_years, "
        "default_change_set_uid) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL)",
        (
            ORG_UID, T_BASE, T_BASE, ORG_NAME, [],
            "Seed organisation for the commodities overview take-home test.",
            # OrganisationConfig dumped by_alias (schemas/organisation.py:31,
            # alias_generator=to_camel) - the key casing stored in the DB.
            psycopg2.extras.Json({
                "hasCommodityImpacts": False,
                "hasCommodityDependencies": False,
                "hasCommodityRisks": False,
            }),
            psycopg2.extras.Json({"baseYear": 2024, "targetYear": 2030}),
        ),
    )

    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO commodity_location_entity (uid, created_at, updated_at, org_uid, "
        "identifier, commodity_type, commodity_subgroup, commodity_code, year_purchased, "
        "sourcing_admin_region_uid, product, supplier, isic_activity, isic_activity_group, "
        "normalised_key) VALUES %s",
        [
            (
                e.uid, e.created_at, e.created_at, ORG_UID, e.identifier,
                e.commodity.type, e.commodity.subgroup, e.commodity.code,
                e.year_purchased,
                e.admin_region.uid if e.admin_region else None,
                e.product, e.supplier, None, None, e.normalised_key,
            )
            for e in seed.entities
        ],
    )

    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO exported_commodity_location (uid, created_at, updated_at, org_uid, "
        "commodity_source_uid, entity_uid, identifier, commodity_type, commodity_subgroup, "
        "commodity_code, year_purchased, sourcing_country_name, sourcing_country_code, "
        "sourcing_administrative_level_1_name, product, supplier, quantity_kilograms, "
        'spend, "group", isic_activity) VALUES %s',
        [
            (
                r.uid, r.created_at, r.created_at, ORG_UID, None, r.entity.uid,
                r.entity.identifier, r.entity.commodity.type,
                r.entity.commodity.subgroup, r.entity.commodity.code,
                r.entity.year_purchased, r.country_name, r.country_code,
                r.admin_1_name, r.product, r.supplier, r.quantity_kilograms,
                r.spend, r.entity.commodity.group, r.entity.commodity.isic_activity,
            )
            for r in seed.exported
        ],
    )

    change_sets = [
        # uid, parent, state, created, processed, published, name, datashape, desc
        (
            V1_UID, None, state_labels["PUBLISHED"], T_V1,
            T_V1 + timedelta(minutes=5), T_V1_PUBLISHED, "Version 1",
            datashape(seed.v1_rows), description(seed, V1_UID),
        ),
        (
            V2_UID, V1_UID, state_labels["DONE"], T_V2,
            T_V2 + timedelta(minutes=5), None, "Version 2",
            datashape(seed.v2_rows), description(seed, V2_UID),
        ),
    ]
    for uid, parent, state, created, processed, published, name, shape, desc in change_sets:
        cur.execute(
            "INSERT INTO change_set (uid, created_at, updated_at, org_uid, parent_uid, "
            "state, processed_at, published_at, unpublished_at, name, description, "
            "datashape) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s)",
            (
                uid, created, published or processed, ORG_UID, parent, state,
                processed, published, name, desc, psycopg2.extras.Json(shape),
            ),
        )

    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO change (uid, created_at, updated_at, org_uid, change_set_uid, "
        "model_type, new_uid, previous_uid, description) VALUES %s",
        [
            (
                c.uid, c.created_at, c.created_at, ORG_UID, c.change_set_uid,
                c.model_type, c.new_uid, c.previous_uid, c.description,
            )
            for c in seed.changes
        ],
    )

    # api/v1/change_set.py `_sync_default_change_set_uid_to_newest_published`
    # (line 509): the org's default is its newest PUBLISHED change set.
    cur.execute(
        "UPDATE organisation SET default_change_set_uid = %s WHERE uid = %s",
        (V1_UID, ORG_UID),
    )


# --------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--reset", action="store_true",
        help="delete the seed organisation's rows before inserting",
    )
    parser.add_argument(
        "--admin-regions", type=Path, default=ADMIN_REGIONS_FILE,
        help=f"admin_region JSON file (default: {ADMIN_REGIONS_FILE})",
    )
    args = parser.parse_args()

    admin_regions = load_admin_regions(args.admin_regions)
    file_countries = {r.country_code for r in admin_regions if r.level == "COUNTRY"}
    missing = sorted(set(COUNTRY_NAMES) - file_countries)
    if missing:
        print(
            f"note: {args.admin_regions} has no COUNTRY row for {', '.join(missing)}; "
            "their commodity sources get no admin region (no map geometry).",
            file=sys.stderr,
        )

    seed = build_seed(admin_regions, random.Random(42))

    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            check_schema(cur)
            cur.execute("SELECT 1 FROM organisation WHERE uid = %s", (ORG_UID,))
            if cur.fetchone():
                if not args.reset:
                    sys.exit(
                        f"organisation {ORG_UID} ({ORG_NAME}) already exists; "
                        "re-run with --reset to replace its rows."
                    )
                reset_org(cur)
            state_labels = {s: enum_label(cur, "changesetstate", s) for s in ("PUBLISHED", "DONE")}
            level_labels = {lv: enum_label(cur, "adminregionlevel", lv) for lv in ("COUNTRY", "REGION")}
            upsert_admin_regions(cur, admin_regions, level_labels)
            insert_seed(cur, seed, state_labels)
    finally:
        conn.close()

    v2_entities = len(seed.v2_rows)
    print(f"organisation        {ORG_UID}  {ORG_NAME}")
    print(f"admin_region        {len(admin_regions)} rows upserted from {args.admin_regions}")
    print(f"Version 1 (published)  {V1_UID}  {len(seed.v1_rows)} commodity sources")
    print(
        f"Version 2 (done)       {V2_UID}  {v2_entities} commodity sources "
        f"({V2_REPLACED} replaced, {V2_TOMBSTONED} removed, {V2_NEW} new)"
    )
    print(f"change rows         {len(seed.changes)}")
    print()
    print(f"Version 1: http://localhost:5678/o/{ORG_UID}/c/{V1_UID}/commodities-overview")
    print(f"Version 2: http://localhost:5678/o/{ORG_UID}/c/{V2_UID}/commodities-overview")


if __name__ == "__main__":
    main()
