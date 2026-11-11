from alembic import context
from sqlalchemy import pool
from src.backend.app.config import settings
from src.backend.app.database import DatabaseFactory
from src.backend.app.models.base import DeclarativeBase

# Migrations need longer timeouts than normal queries (DDL on large tables)
# but should still fail fast if they can't acquire locks.
# Values are in milliseconds to match DatabaseFactory's connect_args format.
# Passed via connect_args options so they are applied at connection-open time
# and do NOT trigger SA 2.0 autobegin before context.configure() is called.
_MIGRATION_CONNECT_OPTIONS = (
    "-c timezone=utc"
    " -c statement_timeout=300000"  # 5 minutes for DDL on large tables
    " -c lock_timeout=30000"  # 30s — fail fast if lock unavailable
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

target_metadata = DeclarativeBase.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    raise NotImplementedError("Offline migrations are not supported")


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = config.attributes.get("connection", None)
    if connectable is None:
        db = DatabaseFactory(
            host=settings.DB_HOST if settings.DB_HOST else "localhost",
            port=settings.DB_PORT,
            database_name=settings.DB_NAME,
            username=settings.DB_USERNAME,
            password=settings.DB_PASSWORD,
            engine_kwargs={
                "poolclass": pool.NullPool,
                "echo": False,
                "connect_args": {"options": _MIGRATION_CONNECT_OPTIONS},
            },
        )
        with db.engine.connect() as conn:
            context.configure(connection=conn, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    else:
        context.configure(
            connection=connectable, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
