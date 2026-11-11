#!/usr/bin/env bash
# Dump the seeded tables into docker/pg-autoload/seed.sql so the compose
# Postgres loads them on first boot (/docker-entrypoint-initdb.d).
#
#   scripts/dump_seed.sh            data only: INSERT statements for the 6
#                                   seeded tables. The schema must already
#                                   exist when the file is replayed, i.e. the
#                                   integrator runs `alembic upgrade head`
#                                   first and restores data after (or orders
#                                   the initdb files so a schema dump comes
#                                   before this one).
#   scripts/dump_seed.sh --schema   full dump of the whole database: schema
#                                   (incl. alembic_version) + data, replayable
#                                   on an empty database by itself.
#   scripts/dump_seed.sh -o FILE    write somewhere else.
#
# Which of the two the compose stack uses is the integrator's call; see
# scripts/README.md.
#
# Connection: DATABASE_URL, or DB_HOST / DB_PORT / DB_USERNAME / DB_PASSWORD /
# DB_NAME (same defaults as scripts/seed.py). Uses a local pg_dump when there
# is one, else the one inside the postgres:16.3 image via docker.

set -euo pipefail

TABLES=(organisation admin_region change_set change commodity_location_entity exported_commodity_location)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$REPO_ROOT/docker/pg-autoload/seed.sql"
SCHEMA=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --schema) SCHEMA=1; shift ;;
        -o|--out) OUT="$2"; shift 2 ;;
        -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

if [[ -n "${DATABASE_URL:-}" ]]; then
    CONN="$DATABASE_URL"
else
    CONN="postgresql://${DB_USERNAME:-postgres}:${DB_PASSWORD:-postgres}@${DB_HOST:-localhost}:${DB_PORT:-5432}/${DB_NAME:-postgres}"
fi

# --column-inserts: INSERTs name their columns, so the file replays against a
# schema whose column order differs from the one it was dumped from.
ARGS=(--no-owner --no-privileges --column-inserts)
if [[ $SCHEMA -eq 1 ]]; then
    # Full dump: pg_dump emits COPY/INSERT data before adding FK constraints,
    # so the organisation <-> change_set FK cycle needs no special handling.
    ARGS+=(--if-exists --clean)
else
    # Data only: organisation.default_change_set_uid -> change_set -> organisation
    # is a cycle, so FK checks are switched off for the load
    # (--disable-triggers; needs a superuser, which the compose postgres is).
    ARGS+=(--data-only --disable-triggers)
    for t in "${TABLES[@]}"; do ARGS+=(-t "$t"); done
fi

mkdir -p "$(dirname "$OUT")"

if command -v pg_dump >/dev/null 2>&1; then
    pg_dump "${ARGS[@]}" "$CONN" > "$OUT"
elif command -v docker >/dev/null 2>&1; then
    # From inside a container "localhost" is the container itself.
    DOCKER_CONN="${CONN/@localhost:/@host.docker.internal:}"
    DOCKER_CONN="${DOCKER_CONN/@127.0.0.1:/@host.docker.internal:}"
    docker run --rm -i postgres:16.3 pg_dump "${ARGS[@]}" "$DOCKER_CONN" > "$OUT"
else
    echo "need pg_dump or docker on PATH" >&2
    exit 1
fi

echo "wrote $OUT ($(wc -l < "$OUT" | tr -d ' ') lines, $([[ $SCHEMA -eq 1 ]] && echo 'schema + data' || echo 'data only'))"
