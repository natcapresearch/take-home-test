from typing import Any

from sqlalchemy import Dialect, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from src.backend.app.schemas.organisation import (
    AnalysisYears,
    OrganisationConfig,
)


class AnalysisYearsField(TypeDecorator[AnalysisYears]):
    """Custom SQLAlchemy field type for AnalysisYears.

    This permits us to pass AnalysisYears instances directly to/from the DB, e.g.

    ```python
    analysis_years = AnalysisYears(
        base_year=2020,
        target_year=2025,
    )
    org = Organisation(
        analysis_years=analysis_years,
        ...
    )

    org = session.query(Organisation).first()
    isinstance(org.analysis_years, AnalysisYears)
    >>> True
    ```
    """

    impl = JSONB
    cache_ok = True

    def process_result_value(
        self,
        value: dict[str, int] | None,
        dialect: Dialect,
    ) -> AnalysisYears | None:
        """Convert from DB -> Python"""
        if value is None:
            return value

        return AnalysisYears.model_validate(value)

    def process_bind_param(
        self,
        value: AnalysisYears | dict[str, int] | None,
        dialect: Dialect,
    ) -> dict[str, int] | None:
        """Convert from Python -> DB"""
        if isinstance(value, AnalysisYears):
            return value.model_dump(by_alias=True)
        return value


class OrganisationConfigField(TypeDecorator[OrganisationConfig]):
    """Custom SQLAlchemy field type for OrganisationConfig.

    This permits us to pass OrganisationConfig instances directly to/from the DB, e.g.

    ```python
    org_config = OrganisationConfig(
        has_commodity_impacts=True,
        ...
    )
    org = Organisation(
        config=org_config,
        ...
    )

    org = session.query(Organisation).first()
    isinstance(org.config, OrganisationConfig)
    >>> True
    ```
    """

    impl = JSONB
    cache_ok = True

    def process_result_value(
        self,
        value: dict[str, Any] | None,
        dialect: Dialect,
    ) -> OrganisationConfig | None:
        """Convert from DB -> Python"""
        if value is None:
            return value

        return OrganisationConfig.model_validate(value)

    def process_bind_param(
        self,
        value: OrganisationConfig | dict[str, Any] | None,
        dialect: Dialect,
    ) -> OrganisationConfig | dict[str, Any] | None:
        """Convert from Python -> DB"""
        if isinstance(value, OrganisationConfig):
            return value.model_dump(by_alias=True)

        return value
