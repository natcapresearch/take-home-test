from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import Any

import sqlalchemy
from pydantic import ConfigDict, Field, SecretStr
from sqlalchemy import Engine
from sqlalchemy.engine import URL
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker
from src.backend.app.config import settings
from src.backend.app.schemas.base import PydanticSchema

logger = settings.logger


@dataclass
class DatabaseConnectionConfig(PydanticSchema):
    """Details required to connect to the database."""

    host: str | None
    port: int
    name: str
    username: str | None
    password: SecretStr | None = Field(default=None)

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class DatabaseFactory:
    config: DatabaseConnectionConfig
    engine_kwargs: dict[str, Any] | None

    uri: URL
    engine: Engine

    session_factory: Callable[..., Session]

    def __init__(
        self,
        host: str | None = "localhost",
        port: int = 5432,
        database_name: str = "postgres",
        username: str | None = None,
        password: SecretStr | None = None,
        engine_kwargs: dict[str, Any] | None = None,
    ):
        """Sets up the database connection and session factory."""
        self.config = DatabaseConnectionConfig.model_validate(
            {
                "host": host,
                "port": port,
                "name": database_name,
                "username": username,
                "password": password,
            },
        )

        self.uri = URL.create(
            drivername="postgresql+psycopg2",
            username=self.config.username,
            password=(
                self.config.password.get_secret_value()
                if self.config.password is not None
                else None
            ),
            host=self.config.host,
            port=self.config.port,
            database=self.config.name,
        )

        engine_kwargs = engine_kwargs or {}
        self.engine_kwargs = {
            "pool_pre_ping": True,
            "echo": settings.DB_ECHO_SQL,
        }
        connect_options = "-c timezone=utc"
        if settings.DB_STATEMENT_TIMEOUT_MS:
            connect_options += (
                f" -c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS}"
            )
        if settings.DB_LOCK_TIMEOUT_MS:
            connect_options += f" -c lock_timeout={settings.DB_LOCK_TIMEOUT_MS}"
        if settings.DB_IDLE_IN_TRANSACTION_TIMEOUT_MS:
            connect_options += (
                f" -c idle_in_transaction_session_timeout="
                f"{settings.DB_IDLE_IN_TRANSACTION_TIMEOUT_MS}"
            )
        self.engine_kwargs["connect_args"] = {"options": connect_options}
        # A caller passing its own poolclass (tests, migrations) manages
        # pooling itself; the service pool is sized from settings.
        if "poolclass" not in engine_kwargs:
            self.engine_kwargs["pool_size"] = settings.DB_CONN_POOL_SIZE
            self.engine_kwargs["max_overflow"] = 0
            self.engine_kwargs["pool_timeout"] = 10
        self.engine_kwargs.update(engine_kwargs)
        self.engine = sqlalchemy.create_engine(
            self.uri.render_as_string(hide_password=False),
            **self.engine_kwargs,
        )

        self.session_factory = sessionmaker(
            self.engine, class_=Session, expire_on_commit=False
        )

    @classmethod
    def from_connection_string(
        cls, connection_string: str, engine_kwargs: dict[str, Any] | None = None
    ) -> "DatabaseFactory":
        """Create a DatabaseFactory instance from a connection string"""
        url = make_url(connection_string)

        return cls(
            host=url.host or "localhost",
            port=url.port or 5432,
            database_name=url.database or "postgres",
            username=url.username,
            password=SecretStr(url.password) if url.password else None,
            engine_kwargs=engine_kwargs,
        )

    def get_session(self) -> Generator[Session, None, None]:
        """Provides a transactional scope around DB actions"""
        with self.session_factory() as session:
            try:
                yield session
            finally:
                session.close()


DB = DatabaseFactory(
    host=settings.DB_HOST if settings.DB_HOST else "localhost",
    port=settings.DB_PORT,
    database_name=settings.DB_NAME,
    username=settings.DB_USERNAME if settings.DB_USERNAME else None,
    password=settings.DB_PASSWORD if settings.DB_PASSWORD else None,
)
logger.debug(
    f"Using database URI: {DB.uri} (pool size: {settings.DB_CONN_POOL_SIZE})"
)
