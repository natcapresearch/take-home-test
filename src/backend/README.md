# backend service

A Python application that serves as the business-logic and data layer for the
dashboard via a FastAPI REST API.

Useful links for tools used:

-   [FastAPI](https://fastapi.tiangolo.com/)
-   [Pydantic](https://docs.pydantic.dev/2.0/blog/pydantic-v2-final/)
-   [SQLAlchemy](https://docs.sqlalchemy.org/en/20/)
-   [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
-   [OpenAPI to TypeScript codegen](https://github.com/hey-api/openapi-ts)

## Structure

The app is broken into distinct layers reflected by the directory structure.
Everything the app needs at runtime should exist within `app/`:

```
src/backend/app/
├── routers/      FastAPI HTTP interfaces (request parsing, auth checks, response shaping)
├── api/v1/       business logic for the v1 routes
├── api/v2/       business logic for the change-set-aware v2 routes
├── schemas/      Pydantic schemas for request/response bodies and DB-shaped objects
├── models/       SQLAlchemy ORM models (one per table)
├── util/         shared helpers: change-set resolution, pagination, request context
├── errors/       exception classes and their HTTP handlers
├── main.py       FastAPI app, middleware and router registration
├── config.py     settings read from the environment / `.env.development`
└── policy_document.yaml  role -> action policies used by `access.py`
```

## Authentication

There is no login. Every request runs as the demo user configured by the
`DEMO_USER_EMAIL`, `DEMO_USER_NICKNAME` and `DEMO_USER_ROLES` settings (see
`config.py`). The user's roles decide which policies in `policy_document.yaml`
apply: `admin` can see and edit every change set state, `viewer` only sees draft
and published change sets.

The organisation a request is for is passed in the `x-org-uid` header.

## Routes

| Method | Path                                            | Purpose                                              |
| ------ | ----------------------------------------------- | ---------------------------------------------------- |
| GET    | `/health`                                       | Liveness check                                       |
| GET    | `/api/v1/users/current/`                        | The demo user                                        |
| GET    | `/api/v1/organisations/{org_uid}/`              | One organisation and its default change set          |
| GET    | `/api/v1/object-permission-set/root/`           | Actions the user may perform with no object          |
| GET    | `/api/v1/object-permission-set/{obj}/{uid}/`    | Actions the user may perform on one object           |
| GET    | `/api/v1/change-set/`                           | One change set, or the organisation's default        |
| GET    | `/api/v1/change-sets/`                          | Paginated change sets                                |
| PATCH  | `/api/v1/change-sets/{change_set_uid}/`         | Rename / describe / change the state of a change set |
| GET    | `/api/v1/change-sets/{change_set_uid}/summary/` | Breakdown of the commodity sources in a change set   |
| GET    | `/api/v2/commodity-sources/`                    | Paginated commodity sources as of a change set       |
| GET    | `/api/v2/commodity-summary/`                    | Summary statistics and filter values                 |
| GET    | `/api/v2/commodity-source-regions-aggregated/`  | Spend / quantity per sourcing region                 |

## Versioning (change sets)

Data is versioned through `change_set` and `change` rows. Each
`commodity_location_entity` is a stable identity; each
`exported_commodity_location` row is that entity's attributes as of one change
set. A `change` row records, per change set, that a row was created (`new_uid`)
or deleted (`previous_uid` only). `util/change_set.py` resolves which rows are
current as of any change set by walking its parent chain.

## Development

```sh
poetry install --with backend,dev
python -m src.backend.cli db upgrade            # apply migrations
uvicorn src.backend.app.main:app --reload       # run the API
python -m src.backend.cli gen-api-spec          # write src/backend/__generated__/openapi.json
python -m src.backend.cli ci check              # ruff + pyright
python -m src.backend.cli ci test               # pytest (needs a Postgres, see conftest.py)
```

Database settings: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`
(see `config.py` for the full list).
