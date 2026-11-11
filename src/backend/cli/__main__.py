import json
import os
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from pathlib import Path

from src.backend.app.config import settings

logger = settings.logger


def create_parser():
    """Create the main argument parser and sub-command parsers."""
    parser = ArgumentParser(description="Main entry point for commands")
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Sub-command to run"
    )

    # db commands
    db_parser = subparsers.add_parser("db", help="Database related commands")
    db_subparsers = db_parser.add_subparsers(
        dest="db_command", required=True, help="Database operation to run"
    )
    db_subparsers.add_parser(
        "current", help="See the current state of the database migrations"
    )
    db_subparsers.add_parser("upgrade", help="Upgrade the database")
    db_generate_parser = db_subparsers.add_parser(
        "generate", help="Generate a new database migration"
    )
    db_generate_parser.add_argument(
        "name", help="Name of the migration", type=str
    )

    # CI commands
    ci_parser = subparsers.add_parser("ci", help="CI related commands")
    ci_subparsers = ci_parser.add_subparsers(
        dest="ci_command", required=True, help="The CI task to run"
    )
    ci_subparsers.add_parser("check", help="Run linters and formatters")
    ci_subparsers.add_parser("test", help="Run pytest")

    # Generate OpenAPI spec command
    subparsers.add_parser("gen-api-spec", help="Generate the OpenAPI spec")

    return parser


def _run_cmds(cmds: list[str]) -> None:
    environ = os.environ.copy()
    for cmd in cmds:
        logger.info(f"Running: {cmd}")
        try:
            subprocess.run(cmd.split(), check=True, env=environ)  # noqa: S603
        except subprocess.CalledProcessError:
            sys.exit(1)


def ci(ns: Namespace):
    if ns.ci_command == "check":
        _run_cmds(
            [
                "ruff check",
                "ruff format --check",
                "pyright src/backend",
            ]
        )
    elif ns.ci_command == "test":
        _run_cmds(["python -m pytest -- src/backend/tests"])
    else:
        logger.error(f"Unknown ci command: {ns.ci_command}")
        sys.exit(1)


def db(ns: Namespace):
    if ns.db_command == "current":
        cmds = [
            "alembic -n backend current -v",
        ]
    elif ns.db_command == "upgrade":
        cmds = [
            "alembic -n backend upgrade head",
            "alembic -n backend current -v",
        ]
    elif ns.db_command == "generate":
        cmds = [
            f'alembic -n backend revision --autogenerate -m "{ns.name}"',
            "ruff check --fix src/backend/migrations/versions",
            "ruff format src/backend/migrations/versions",
        ]
    else:
        logger.error(f"Unknown db command: {ns.db_command}")
        sys.exit(1)

    _run_cmds(cmds)


def gen_api_spec(ns: Namespace):
    from src.backend.app.main import app

    resources_dir = Path("src/backend/__generated__")
    Path.mkdir(resources_dir, parents=True, exist_ok=True)

    spec = app.openapi()

    # NOTE: do not run `ruff format` over this file. It parses JSON as Python
    # and rewrites it with trailing commas, which is not valid JSON.
    spec_file = Path(resources_dir / Path("openapi.json"))
    with Path.open(spec_file, "w") as _f:
        json.dump(spec, _f, indent=2)
    logger.info(f"OpenAPI spec written to: {spec_file}")


def main():
    parser = create_parser()
    ns: Namespace = parser.parse_args()

    command_lookup: dict[str, Callable[[Namespace], None]] = {
        "ci": ci,
        "db": db,
        "gen-api-spec": gen_api_spec,
    }

    if command := command_lookup.get(ns.command):
        command(ns)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
