# AI-first Full-Stack Engineer — take-home test

> **The task is in [TASK.md](TASK.md).** This file explains how to install,
> run and test the repository.
>
> **Licence:** proprietary — see [LICENSE](LICENSE). Provided for this
> assessment only; © Natcap Research Ltd.

This repository is a small, self-contained slice of a nature-risk analytics
platform: one dashboard page (**Commodities Overview**) with its full vertical
stack — React dashboard → GraphQL server → FastAPI backend → Postgres — plus a
change-set ("versioning") panel. It runs entirely on your machine with Docker;
there is no login, no cloud account and no external service except the
OpenStreetMap tiles the map draws.

## 1. Prerequisites

You need nothing from any other repository. Everything below is installed
from public sources.

### To run the app (required)

| Tool | Version | Install |
|---|---|---|
| Git | any | <https://git-scm.com/downloads> |
| Docker with Compose v2 | Docker Desktop 4.x (macOS/Windows) or Docker Engine 24+ with the `docker compose` plugin (Linux) | <https://docs.docker.com/get-docker/> |

Give Docker at least **4 GB of memory and ~5 GB of free disk**. The first
build downloads base images and packages, so it needs internet access; after
that only the map's background tiles (openstreetmap.org) are fetched from the
network.

Ports **5678, 4000, 8000 and 5432** must be free on your machine (if 5432 is
taken by a local Postgres, stop it or change the host port in
`docker-compose.yaml`).

### To change code and run the tests (required for the task)

| Tool | Version | Install |
|---|---|---|
| Python | **3.12.x** (not 3.13) | <https://www.python.org/downloads/> or `pyenv install 3.12` |
| Poetry | 1.8 or 2.x | <https://python-poetry.org/docs/#installation> |
| Node.js | **22.x** (`.nvmrc` says 22.16.0) | <https://nodejs.org/> or `nvm install 22` |
| pnpm | 9.12.3 (pinned in `package.json`) | `corepack enable` (ships with Node) — it then installs the pinned pnpm on first use |

Check with:

```sh
git --version && docker compose version
python3.12 --version && poetry --version
node --version && corepack enable && pnpm --version
```

## 2. Install

```sh
git clone <this repository> take-home-test
cd take-home-test

poetry install          # Python packages into a virtualenv managed by Poetry
pnpm install            # Node packages into ./node_modules
pnpm run gen            # generate the TypeScript types from the backend + GraphQL schema
```

`pnpm run gen` must be run once before type checks or tests, and again after
you change a backend Pydantic schema, `src/graphql/resources/schema.graphql`
or any `src/ui/dashboard/src/graphql/*.graphql` document. The generated
files are git-ignored.

If you only want to *see* the app, you can skip this section entirely and go
to **3. Run**.

## 3. Run

```sh
docker compose up --build
```

The first run takes a few minutes (image builds). When the log shows
`dashboard-1 | Application startup complete.`, open

**<http://localhost:5678>**

You land on the organisation **Example Foods Ltd** on the **Commodities
Overview** page, showing the latest version of its data. The URL names the
version (change set) you are looking at; the published one is

```
http://localhost:5678/o/a4e22a6a-a062-4436-90c6-c51635c03fa7/c/d4abecb4-1fc3-41a6-a45c-31028a7ffdd8/commodities-overview
```

### What you should see in your browser

![The Commodities Overview page: stat cards, the Map View tab with the global sourcing map, and the commodity charts](docs/app.png)

The database is created and seeded automatically on the first start (from
`docker/pg-autoload/seed.sql`). Useful commands:

```sh
docker compose logs -f                 # follow all logs
docker compose down                    # stop (data is kept)
docker compose down -v                 # stop and wipe the database (re-seeded on next start)
DEMO_USER_ROLES=viewer docker compose up   # run as a read-only user (see "Users and permissions")
```

### What is running

| Service     | Port | What it is                                                                 |
|-------------|------|----------------------------------------------------------------------------|
| `dashboard` | 5678 | FastAPI static server for the built React app; proxies `/api` → GraphQL    |
| `graphql`   | 4000 | Apollo Server (TypeScript); the only thing the dashboard talks to          |
| `backend`   | 8000 | FastAPI + SQLAlchemy; the only thing that talks to Postgres                |
| `postgres`  | 5432 | Postgres 16                                                                |
| `migrate`   | —    | one-shot: `alembic upgrade head` before the backend starts                 |

GraphQL playground: <http://localhost:4000/>. Backend OpenAPI docs:
<http://localhost:8000/docs>. Database: `postgres://postgres:postgres@localhost:5432/postgres`.

### Run with hot reload (while working on the task)

After **2. Install**:

```sh
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
```

and open **<http://localhost:1234>** instead (the Parcel dev server; it
proxies `/api` to the GraphQL service). Edits under `src/` reload in place in
all three services. After changing a schema or a `.graphql` document, run
`pnpm run gen` on your machine again — the generated files are mounted into
the containers.

## 4. Test

All commands run from the repository root, after **2. Install**.

### TypeScript (GraphQL server + dashboard)

```sh
pnpm run check      # type-check both projects (tsc)
pnpm run lint       # eslint + prettier       (pnpm run fix to auto-fix)
pnpm test           # jest
```

### Python (backend)

The backend tests need a Postgres to create test databases in. Use the one
from Compose (`docker compose up -d postgres`) or a throwaway one:

```sh
docker run -d --name test-pg -e POSTGRES_PASSWORD=postgres -p 5433:5432 postgres:16.3
export DB_HOST=localhost DB_PORT=5433 DB_USERNAME=postgres DB_PASSWORD=postgres
```

then

```sh
poetry run pyright                                   # strict type check
poetry run ruff check src/backend                    # lint
poetry run python -m pytest -q src/backend/tests
```

Use `python -m pytest`, not bare `pytest`: `src/backend` is imported as a
namespace package from the repository root. `docker rm -f test-pg` when
done.

### Everything at once

```sh
pnpm run verify                              # test + fix + check (TypeScript)
poetry run python -m src.backend.cli ci check   # ruff + pyright (Python)
```

## How the page works

```
src/ui/dashboard/src/page/Organisation/CommoditiesOverview.tsx
  └─ OrganisationCommoditySources        (src/ui/dashboard/src/graphql/organisationCommoditySources.graphql)
  └─ AggregatedCommoditySourceRegions    (…/aggregatedCommoditySourceRegions.graphql)
        │  resolved by src/graphql/src/resolvers.ts
        │  which calls the backend via src/graphql/src/dataSources/backendApi.ts
        ▼
GET /api/v2/commodity-sources/                      src/backend/app/routers/api_v2/…
GET /api/v2/commodity-summary/                      → src/backend/app/api/v2/commodity_location.py
GET /api/v2/commodity-source-regions-aggregated/
        ▼
commodity_location_entity ─┬─ exported_commodity_location   (the rows you see)
                           └─ admin_region                   (map polygons)
change_set ── change                                         (which rows are "current")
organisation
```

Types flow in one direction and are generated, never hand-written:

```
backend Pydantic schemas ──(gen-api-spec)──▶ src/backend/__generated__/openapi.json
     ──(openapi-ts)──▶ src/graphql/__generated__/backend/types.gen.ts
src/graphql/resources/schema.graphql + src/ui/dashboard/src/graphql/*.graphql
     ──(graphql-codegen)──▶ src/graphql/__generated__/*, src/common/__generated__/client-types.ts
```

Run `pnpm run gen` after changing a backend schema, the GraphQL schema or a
`.graphql` document.

### Versioning (change sets)

Every row the page shows belongs to a **change set**. A change set is a list
of `change` rows (`model_type`, `new_uid`, `previous_uid`) on top of its
parent; `src/backend/app/util/change_set.py` resolves which
`exported_commodity_location` row is current for each entity in a given
change set. The seed creates two:

| Name      | State       | uid                                    |
|-----------|-------------|----------------------------------------|
| Version 1 | `PUBLISHED` | `d4abecb4-1fc3-41a6-a45c-31028a7ffdd8` |
| Version 2 | `DONE`      | `f7e34b50-8895-4dcf-a96d-c8af2e461625` |

Version 2 replaces the amounts of 10 commodity sources, removes 2 and adds 3.
The panel in the top bar lists versions, lets you switch the page to one
(`/c/<change-set-uid>/` in the URL), rename/describe it, and publish or
unpublish it (`PATCH /api/v1/change-sets/{uid}/`). Publishing makes a version
the organisation's default.

### Users and permissions

There is no login. The backend injects one principal into every request from
environment variables (`DEMO_USER_EMAIL`, `DEMO_USER_NICKNAME`,
`DEMO_USER_ROLES`; see `src/backend/app/middleware.py`). Permissions are
role-based and declared in `src/backend/app/policy_document.yaml`;
`src/backend/app/access.py` evaluates them and the
`/api/v1/object-permission-set/…` routes expose them to the UI, which uses
them to enable or hide controls (e.g. the Publish button).

Try `DEMO_USER_ROLES=viewer docker compose up` for a read-only user who only
sees published versions.

## Seed data

`scripts/seed.py` generates the demo organisation deterministically (fixed
uids, fixed RNG): 120 commodity sources across 12 commodities and 15
countries, two change sets, and the country boundaries from
`scripts/data/admin_regions.json`. `docker/pg-autoload/seed.sql` is its
output, loaded by Postgres on first boot. To change the data, edit the script,
then regenerate the dump:

```sh
cp example.env.development .env.development   # DB_HOST=localhost
poetry run python -m src.backend.cli db upgrade
poetry run python scripts/seed.py --reset
scripts/dump_seed.sh --schema   # writes docker/pg-autoload/seed.sql
```

See `scripts/README.md`. (`dump_seed.sh` is a bash script; on Windows run it
from WSL or Git Bash. You do not need to regenerate the dump to complete the
task.)

## Layout

```
src/backend/      FastAPI app (app/), alembic migrations, CLI (`python -m src.backend.cli`), tests
src/graphql/      Apollo server (src/), schema (resources/schema.graphql), codegen config
src/ui/dashboard/ React app (src/), its static server (main.py), index.html
src/ui/common/    shared UI components
src/common/       TypeScript shared between graphql and ui (+ generated client types)
scripts/          seed script, admin-region data, dump helper
docker/           Postgres init: schema + seed data loaded on first start (pg-autoload/)
```
