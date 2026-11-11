import uuid
from datetime import datetime
from typing import Any

from pydantic.alias_generators import to_snake
from sqlalchemy import (
    DateTime,
    Select,
    UnaryExpression,
    nulls_first,
    nulls_last,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql import func
from src.backend.app.config import settings
from src.backend.app.util import pagination
from src.backend.app.util.enums import SortOrder

logger = settings.logger


def _declarative_constructor(obj: Any, **kwargs: dict[str, Any]):
    """
    Wrapper for declarative_base constructor to allow easy ignoring of specific extra
    kwargs, eg API metadata.
    """
    for k, v in kwargs.items():
        if k in ["meta"]:
            continue
        setattr(obj, k, v)


# All models for the main application should inherit from this base class.
DeclarativeBase = declarative_base(constructor=_declarative_constructor)


class BaseModel(DeclarativeBase):
    """Base model class that all DB models should inherit from."""

    __abstract__ = True

    policy_resource_type: str | None = None
    """
    The policy-document resource type corresponding to this model.
    """

    uid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        return to_snake(cls.__name__).lower()

    @declared_attr.directive
    @classmethod
    def __matching_columns__(cls) -> list[Mapped[Any]]:
        return [cls.uid]

    @classmethod
    def paginate(
        cls,
        db: Session,
        select_query: Select[Any],
        sort_on: str | list[str] | None = "created_at",
        sort_order: SortOrder | list[SortOrder] | None = SortOrder.DESC,
        cursor: pagination.PaginationCursor | None = None,
        limit: int = settings.DEFAULT_PAGE_SIZE,
        reverse: bool = False,
        sort_alias: str | None = None,
        extra_sort_columns: "dict[str, Any] | None" = None,
        count_query: "Select[Any] | None" = None,
    ) -> pagination.Paginator:
        """
        Convenience method to make pagination available on all models.
        """
        return pagination.Paginator(
            cls,
            db,
            select_query,
            sort_on or "created_at",
            sort_order or SortOrder.DESC,
            cursor,
            limit,
            reverse,
            sort_alias,
            extra_sort_columns,
            count_query,
        )

    @classmethod
    def order_by(
        cls,
        sort_on: str = "created_at",
        sort_order: SortOrder = SortOrder.DESC,
    ) -> UnaryExpression[Any]:
        """
        Helper function to generate the order_by clause for a query accounting for the
        default "created_at" ordering required for stable sorting in cursor pagination.
        If sort_on is specified it will be added to the order_by clause.
        """
        if sort_order not in SortOrder:
            raise ValueError(f"Invalid sort_order: {sort_order}")

        if sort_on is None:  # type: ignore
            sort_on = "created_at"

        sort_on = to_snake(sort_on).lower()

        if not hasattr(cls, sort_on):
            raise AttributeError(
                f"{cls.__name__} has no '{sort_on}' column to sort on."
            )

        match sort_order:
            case SortOrder.ASC:
                order = nulls_first(
                    getattr(getattr(cls, sort_on), sort_order.value)()
                )
            case SortOrder.DESC:
                order = nulls_last(
                    getattr(getattr(cls, sort_on), sort_order.value)()
                )

        return order

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.uid}>"
