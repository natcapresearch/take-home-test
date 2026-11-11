from typing import Literal

import structlog
from pydantic import (
    Field,
    SecretStr,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.backend.app.logging import create_logger


class Settings(BaseSettings):
    """
    Management of environment variables and logging configuration.

    Values are read from the environment, falling back to a `.env.development`
    file in the working directory when one exists.
    """

    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
        env_file=".env.development",
        env_file_encoding="utf-8",
    )

    APP_NAME: str = "backend"
    DEBUG: bool = Field(
        default=False,
        description="Human-readable console logging and verbose error messages.",
    )

    API_PREFIX: str = Field(default="/api")

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )

    @computed_field
    @property
    def logger(self) -> structlog.typing.FilteringBoundLogger:
        return create_logger(self.DEBUG, self.LOG_LEVEL)

    DB_HOST: str | None = Field(default=None)
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="postgres")
    DB_USERNAME: str | None = Field(default=None)
    DB_PASSWORD: SecretStr | None = Field(default=None)
    # Slightly lower than the local postgres default of 100 connections.
    DB_CONN_POOL_SIZE: int = Field(default=98)
    DB_STATEMENT_TIMEOUT_MS: int = Field(
        default=30000,
        description="Maximum execution time for any statement in milliseconds. 0 disables.",
    )
    DB_LOCK_TIMEOUT_MS: int = Field(
        default=5000,
        description="Maximum time to wait for a lock in milliseconds. 0 disables.",
    )
    DB_IDLE_IN_TRANSACTION_TIMEOUT_MS: int = Field(
        default=60000,
        description="Maximum time a session can stay idle in a transaction in milliseconds. 0 disables.",
    )
    DB_ECHO_SQL: bool = Field(
        default=False,
        description="Enable SQLAlchemy query logging. Set to true to log all SQL queries.",
    )

    @model_validator(mode="after")
    def validate_db_password(self):
        if self.DB_PASSWORD is not None and self.DB_USERNAME is None:
            raise ValueError("DB_USERNAME must be set if DB_PASSWORD is set")
        return self

    BACKEND_CORS_ALLOWED_ORIGINS: list[str] = Field(default_factory=list)

    @field_validator("BACKEND_CORS_ALLOWED_ORIGINS")
    @classmethod
    def include_trailing_slash(cls, urls: list[str]) -> list[str]:
        duplicated_urls: list[str] = []
        for url in urls:
            if url.endswith("/"):
                other_url = url.rstrip("/")
            else:
                other_url = url + "/"
            duplicated_urls.extend([url, other_url])
        return duplicated_urls

    DEFAULT_PAGE_SIZE: int = Field(
        default=50,
        description="The default page size for pagination",
    )
    MAX_PAGE_SIZE: int = Field(
        default=10000,
        description="The maximum page size for pagination",
    )

    DEMO_USER_EMAIL: str = Field(
        default="demo@example.com",
        description="Email of the single demo user every request runs as.",
    )
    DEMO_USER_NICKNAME: str = Field(
        default="Demo User",
        description="Display name of the demo user.",
    )
    DEMO_USER_ROLES: str = Field(
        default="admin",
        description=(
            "Comma-separated roles of the demo user, matched against the "
            "policies in policy_document.yaml (admin or viewer)."
        ),
    )

    @computed_field
    @property
    def demo_user_roles(self) -> list[str]:
        return [
            role.strip()
            for role in self.DEMO_USER_ROLES.split(",")
            if role.strip()
        ]


settings = Settings()
