# scripts

Seed data for the commodities overview slice.

## What `seed.py` creates

One organisation, **Example Foods Ltd** (`config` has the three commodity flags
off, no authorised email domains, analysis years 2024 -> 2030), and two versions
of its commodity sourcing data:

| | uid | state | content |
|---|---|---|---|
| Version 1 | `d4abecb4-1fc3-41a6-a45c-31028a7ffdd8` | `PUBLISHED` (the org's `default_change_set_uid`) | 120 commodity sources: 12 commodities (coffee, cocoa, palm oil, soy, sugar cane, wheat, maize, rice, cotton, natural rubber, beef, softwood timber) x 10, across 15 sourcing countries, 3 suppliers and 3 products per commodity, purchase years 2022-2024, ~10% without quantity and ~10% without spend |
| Version 2 | `f7e34b50-8895-4dcf-a96d-c8af2e461625` | `DONE` (child of Version 1) | 10 sources replaced with new values (4 of them moved to another country, 3 with another supplier, all with new quantity/spend), 2 sources removed, 3 new sources: 121 in total |

Organisation uid: `a4e22a6a-a062-4436-90c6-c51635c03fa7`.

Those uids are `uuid.uuid5` from a fixed namespace (`stable_uid` in
`seed.py`), so they are the same on every run and on every machine. The script
prints them, together with the dashboard URLs:

```
http://localhost:5678/o/a4e22a6a-a062-4436-90c6-c51635c03fa7/c/d4abecb4-1fc3-41a6-a45c-31028a7ffdd8/commodities-overview
http://localhost:5678/o/a4e22a6a-a062-4436-90c6-c51635c03fa7/c/f7e34b50-8895-4dcf-a96d-c8af2e461625/commodities-overview
```

Rows are written the way the platform's versioned reads expect
(`src/backend/app/util/change_set.py` `change_set_query`): each
`commodity_location_entity` and `exported_commodity_location` row is tied to
the change set it belongs to by a `change` row (`model_type` = table name,
`new_uid` = the row). A replacement in Version 2 is a new
`exported_commodity_location` row for the same `entity_uid` with a later
`created_at` (plus `previous_uid` = the Version 1 row); a removal is a `change`
with `new_uid` NULL and `previous_uid` = the row.

`admin_region` rows come from `scripts/data/admin_regions.json`, see
`scripts/data/README.md`: the committed file is a two-country placeholder, the
integrator supplies the real one.

## Running

Needs Python 3.12 with `psycopg2-binary` (in the backend poetry environment)
and a database with the schema already created (`alembic upgrade head`).

```sh
# connection: DATABASE_URL, or the parts (shown with their defaults)
export DB_HOST=localhost DB_PORT=5432 DB_USERNAME=postgres DB_PASSWORD=postgres DB_NAME=postgres

poetry run python scripts/seed.py            # refuses if the organisation exists
poetry run python scripts/seed.py --reset    # delete the organisation's rows, then seed
poetry run python scripts/seed.py --admin-regions path/to/real_admin_regions.json --reset
```

`--reset` deletes only the seed organisation's rows (`change`, `change_set`,
`exported_commodity_location`, `commodity_location_entity`, `organisation`);
`admin_region` is shared reference data and is upserted, never deleted.

## Regenerating `docker/pg-autoload/seed.sql`

The compose Postgres replays `docker/pg-autoload/*.sql` once, when its data
volume is first created. After changing `seed.py` or the admin regions file,
seed a database and dump it:

```sh
poetry run python scripts/seed.py --reset
scripts/dump_seed.sh             # data only, 6 tables, INSERT statements
scripts/dump_seed.sh --schema    # full schema + data dump of the database
```

Which one to commit is the integrator's decision:

- **data only** (`--data-only --inserts --disable-triggers`): the schema has to
  exist before the file is replayed, so the stack must run `alembic upgrade
  head` before restoring the data (the compose `migrate` service runs after
  Postgres has already replayed initdb files, so this needs reordering, or a
  schema dump placed before `seed.sql` in `docker/pg-autoload/`).
- **schema + data** (`--schema`): self-contained, replayable on an empty
  database; includes `alembic_version` so a later `alembic upgrade head` is a
  no-op. Must be re-dumped whenever a migration changes the schema.

`dump_seed.sh` uses a local `pg_dump` when there is one, otherwise the one in
the `postgres:16.3` image through docker (`localhost` is rewritten to
`host.docker.internal`). Then `docker compose down -v && docker compose up` to
recreate the volume from the new file.

## Changing the data

Everything is generated from `random.Random(42)` and the constants at the top
of `seed.py` (`COMMODITIES`, `COUNTRY_NAMES`, `ROWS_PER_COMMODITY`,
`V2_REPLACED`, `V2_TOMBSTONED`, `V2_NEW`, `NULL_SHARE`). Edit those, re-run
with `--reset`, re-dump. Row uids are derived from identifiers, so adding rows
at the end does not change existing uids; changing `COMMODITIES` order does.

`scripts/_dev/` holds what was used to test the script against a throwaway
Postgres (`schema_for_seed_test.sql`, a hand-written stand-in for the alembic
schema, and `verify_seed.sql`, a raw-SQL port of `change_set_query` that
counts what each version resolves). Safe to delete.
