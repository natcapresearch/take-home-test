import base64
import json
import operator
import time
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import (
    AwareDatetime,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_serializer,
    model_validator,
)
from sqlalchemy import (
    ColumnElement,
    DateTime,
    Enum,
    Float,
    Integer,
    Select,
    String,
    and_,
    distinct,
    func,
    or_,
    select,
    tuple_,
)
from sqlalchemy.orm import InstrumentedAttribute, Session, aliased
from src.backend.app.config import settings
from src.backend.app.schemas.base import PydanticSchema
from src.backend.app.util.enums import SortOrder
from typing_extensions import Self

if TYPE_CHECKING:
    from src.backend.app.models.base import BaseModel

logger = settings.logger


DEFAULT_PRIMARY_SORT = (
    "created_at"  # Default order_by column, can be overridden
)
DEFAULT_SECONDARY_SORT = "uid"  # Secondary order_by column used as a tie-breaker ensuring unique rows, always used


class SecondarySort(PydanticSchema):
    order: SortOrder
    order_on: str


SECONDARY_SORTS: dict[str, SecondarySort] = {}


def sort_with_tiebreak(
    sort_on: str,
    sort_order: SortOrder,
    *tiebreaks: str,
) -> tuple[list[str], list[SortOrder]]:
    """
    Sort on `sort_on`, then on each of `tiebreaks` ascending in turn, as
    `paginate` arguments. A tiebreak equal to `sort_on` is skipped.

    Rows tied on `sort_on` would otherwise fall through to the uid tie-breaker,
    and uids are random per insert, so the same data (e.g. a re-upload) lists
    tied rows in a different order each time. A stable business key such as an
    identifier from the data template fixes that order. Unlike a SECONDARY_SORTS
    entry, which replaces the uid tie-breaker, uid is still appended after it,
    so rows tied on all of them remain uniquely ordered.
    """
    sort_columns = [sort_on]
    sort_orders = [sort_order]
    for tiebreak in tiebreaks:
        if tiebreak not in sort_columns:
            sort_columns.append(tiebreak)
            sort_orders.append(SortOrder.ASC)
    return sort_columns, sort_orders


class PaginationError(Exception): ...


class PaginationCursor(PydanticSchema):
    """
    Class for handling pagination cursors. The cursor is a base64 encoded JSON string
    that contains the cursor data as a list of key-value pairs. Base64 url-safe
    encoding is used to ensure that the cursor can be safely used in URLs and makes
    cursors opaque to the user. However, cursors are not encrypted or tampered proof
    and should not be used to store sensitive data. If this is a requirement in future,
    consider using a signed token (eg JWT) or similar. The class is a Pydantic schema
    in order to take advantage of Pydantic's validation and serialisation capabilities
    for automatic conversion between the cursor dictionary and the base64 encoded string.
    """

    cursor_values: list[
        tuple[str, str | int | float | UUID | AwareDatetime | None]
    ] = Field()
    sort_order: SortOrder = Field(default=SortOrder.DESC)
    sort_orders: list[SortOrder] | None = Field(default=None)
    sort_alias: str | None = Field(default=None)
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def create_cursor(  # noqa: C901
        cls,
        item: "BaseModel",
        sort_on: list[str] | None = None,
        sort_order: SortOrder | list[SortOrder] = SortOrder.DESC,
        from_cursor: "PaginationCursor | None" = None,
        sort_alias: str | None = None,
        extra_values: dict[str, Any] | None = None,
    ) -> "PaginationCursor":
        """
        Helper function to create a cursor for a model instance. Optionally built from
        a prior cursor (for stable sorting) using the `from_cursor` parameter.

        Args:
            item: The model instance to create a cursor for.
            sort_on: The columns to sort on.
            sort_order: The sort order (ASC or DESC).
            from_cursor: An existing cursor to derive column names from.
            sort_alias: An optional alias for the sort column.
            extra_values: Extra column values not present as model attributes,
                keyed by logical column name (e.g. ``{"concern_score": 3}``).
                These are checked before falling back to ``getattr(item, col)``.
        """
        if from_cursor:
            sort_on = [col for col, _ in from_cursor.cursor_values]
            sort_alias = from_cursor.sort_alias
            if isinstance(sort_order, list):
                sort_orders = sort_order.copy()
            else:
                sort_orders = (
                    from_cursor.sort_orders.copy()
                    if from_cursor.sort_orders
                    else [from_cursor.sort_order] * len(sort_on)
                )
        else:
            if not sort_on or any(x is None for x in sort_on):  # type: ignore
                logger.debug("No sort_on provided, using default sort columns")
                sort_on = [
                    DEFAULT_PRIMARY_SORT,
                    DEFAULT_SECONDARY_SORT,
                ]

            if isinstance(sort_order, list):
                sort_orders = sort_order.copy()
            else:
                sort_orders = [sort_order] * len(sort_on)

        sort_on = sort_on.copy()

        if len(sort_orders) == 1 and len(sort_on) > 1:
            sort_orders = sort_orders * len(sort_on)

        if sort_on[-1] != DEFAULT_SECONDARY_SORT:
            sort_on.append(DEFAULT_SECONDARY_SORT)
            sort_orders.append(sort_orders[0])

        if len(sort_orders) != len(sort_on):
            raise ValueError("sort_order must match sort_on length")

        for order in sort_orders:
            if order not in SortOrder:
                raise ValueError("Invalid sort order")

        cursor_values: list[
            tuple[str, str | int | float | UUID | datetime | None]
        ] = []
        for col in sort_on:
            if extra_values is not None and col in extra_values:
                cursor_values.append((col, extra_values[col]))
            else:
                cursor_values.append((col, getattr(item, col)))

        return PaginationCursor(
            cursor_values=cursor_values,
            sort_order=sort_orders[0],
            sort_orders=sort_orders,
            sort_alias=sort_alias,
        )

    @field_validator("cursor_values", mode="before")
    @classmethod
    def validate_cursor_values(
        cls, vals: str | list[tuple[str, str | int | float | datetime]]
    ):
        if vals is None:  # type: ignore
            raise ValueError("Cannot create cursor with no values")

        if not isinstance(vals, list):
            raise TypeError("Cursor values must be a list of tuples")

        for i, (col, v) in enumerate(vals):
            if isinstance(v, datetime) and v.tzinfo is None:
                vals[i] = (col, v.replace(tzinfo=timezone.utc))

        return vals

    @model_validator(mode="wrap")
    @classmethod
    def deserialise_model(
        cls,
        vals: str | list[tuple[str, str | int | float | datetime]],
        handler: Callable[..., Self],
    ) -> Self:
        """
        Performs deserialisation from a base64 encoded cursor string to a
        PaginationCursor object. Runs automatically when FastAPI receives a cursor
        query string parameter.
        """
        if isinstance(vals, str):
            vals = cls.deserialise_cursor(vals)

        try:
            return handler(vals)
        except (ValidationError, ValueError) as e:
            logger.debug(str(e))
            logger.exception(f"Failed to deserialise cursor: {vals}")
            raise ValueError("Failed to deserialise cursor") from e

    @classmethod
    def deserialise_cursor(
        cls, cursor: str
    ) -> list[tuple[str, str | int | float | datetime]]:
        """
        Internal helper to deserialise a base64 encoded cursor string to a dict
        object compatible with the PaginationCursor schema.
        """
        try:
            json_data = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode(
                "utf-8"
            )
        except (UnicodeDecodeError, ValueError) as e:
            logger.exception(f"Failed to deserialise cursor: {cursor}")
            raise PaginationError("Failed to deserialise cursor") from e

        try:
            model_dict = json.loads(json_data)
        except json.JSONDecodeError as e:
            logger.exception(f"Failed to deserialise cursor: {cursor}")
            raise PaginationError("Failed to deserialise cursor") from e

        return model_dict

    @model_serializer(mode="wrap", when_used="always")
    def serialise(
        self,
        handler: Callable[..., str],
    ) -> str:
        """
        Performs serialisation from a PaginationCursor object to a base64 encoded
        cursor string. Run automatically by FastAPI when we return a cursor in
        response headers.
        """
        json_data = jsonable_encoder(handler(self))
        cursor = base64.urlsafe_b64encode(
            json.dumps(json_data).encode("utf-8")
        ).decode("utf-8")
        return cursor


class Paginator:
    """
    Handles cursor-based pagination for SQLAlchemy queries. Returns a Paginator object
    providing access to the paginated data, cursor, and metadata.

    Extra sort columns
    ------------------
    When you need to sort by a column that does not live on the primary model
    (e.g. a score value from a joined table), pass ``extra_sort_columns``.

    The caller is responsible for:

    1. Adding the extra column to the ``select_query`` via ``add_columns()``,
       labelling it ``_extra_<logical_name>`` (e.g. ``_extra_concern_score``).
    2. Passing ``extra_sort_columns = {"concern_score": <ColumnElement>}`` where
       the ``ColumnElement`` is the same expression used in step 1 (before
       ``.label()`` is applied), so that it can be reused in ORDER BY and WHERE
       clauses inside the inner pagination query.

    The paginator will then:
    * project those extra columns through the outer query,
    * read their values via ``db.execute()`` (instead of ``db.scalars()``),
    * supply the captured values to ``PaginationCursor.create_cursor`` so that
      cursors encode the extra sort field correctly.
    """

    model: "BaseModel"
    _sort_specs: list[tuple[str, SortOrder]]
    _extra_sort_columns: dict[str, ColumnElement[Any]]
    _extra_values_by_uid: dict[str, dict[str, Any]]
    _select_query: Select[Any]
    _pagination_query: Select[Any]
    _total_count_query: Select[Any]
    _reverse: bool
    _has_more: bool
    query: Select[Any]
    total_count: int
    limit: int
    results: Sequence["BaseModel"]
    count: int
    cursor: PaginationCursor | None
    next_cursor: PaginationCursor | None = None
    prev_cursor: PaginationCursor | None = None

    sort_alias: str | None = None

    query_time: float
    count_time: float

    def __str__(self) -> str:
        sort_on, sort_order = self._sort_specs[0]
        return f"""
        Paginator: {self.model.__name__} by {sort_on} {sort_order.name}
        Reversed?: {self._reverse}
        Total count: {self.total_count}
        Count: {self.count}
        Next cursor: {self.next_cursor}
        Prev cursor: {self.prev_cursor}
        Results: {self.results}

        Query time: {self.query_time:.3f}s
        Count time: {self.count_time:.3f}s
        """

    def __init__(
        self,
        model: "type[BaseModel]",
        db: Session,
        select_query: Select[Any],
        sort_on: str | list[str],
        sort_order: SortOrder | list[SortOrder],
        cursor: PaginationCursor | None = None,
        limit: int = settings.DEFAULT_PAGE_SIZE,
        reverse: bool = False,
        sort_alias: str | None = None,
        extra_sort_columns: dict[str, ColumnElement[Any]] | None = None,
        count_query: Select[Any] | None = None,
    ):
        """
        Build the required queries, get paginated query results and return the Paginator object.

        Args:
            model: The SQLAlchemy model class to paginate.
            db: Database session.
            select_query: Base SELECT query (may include joins / ``add_columns`` calls).
            sort_on: Primary sort column name.
            sort_order: Sort direction (ASC or DESC).
            cursor: Pagination cursor from a previous page.
            limit: Page size.
            reverse: True when paginating backwards (using a ``before`` cursor).
            sort_alias: Optional alias carried through cursors.
            extra_sort_columns: Mapping of logical sort-field name to its
                ``ColumnElement`` for columns that do not belong to *model*.
                The corresponding column must already be present in
                *select_query* via ``add_columns(expr.label("_extra_<name>"))``.
            count_query: Optional simpler query for computing total count.
                When provided, this query is used for COUNT instead of
                deriving from *select_query*. Useful when *select_query*
                contains LEFT JOINs that don't affect row count.
        """
        self.model = model
        self._select_query = select_query
        self._count_query = count_query
        self._reverse = reverse
        self.cursor = cursor
        self.limit = limit
        self.sort_alias = sort_alias
        self._extra_sort_columns = extra_sort_columns or {}
        self._extra_values_by_uid = {}

        self._sort_specs = self._build_sort_specs(model, sort_on, sort_order)

        self._build_query()
        self._get_total_count(db)
        self._paginate(db)
        logger.debug(str(self))

    @staticmethod
    def normalise_sort_args(
        sort_on: str | list[str] | None,
        sort_order: SortOrder | list[SortOrder] | None,
        cursor: PaginationCursor | None = None,
        default_sort_on: str = DEFAULT_PRIMARY_SORT,
        default_sort_order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[str], list[SortOrder]]:
        if isinstance(sort_on, list):
            sort_columns = sort_on.copy()
        elif isinstance(sort_on, str):
            sort_columns = [sort_on]
        elif cursor is not None:
            sort_columns = [column for column, _ in cursor.cursor_values]
        else:
            sort_columns = [default_sort_on]

        if isinstance(sort_order, list):
            sort_orders = sort_order.copy()
        elif isinstance(sort_order, SortOrder):
            sort_orders = [sort_order] * len(sort_columns)
        elif cursor is not None and cursor.sort_orders:
            sort_orders = cursor.sort_orders[: len(sort_columns)].copy()
        else:
            sort_orders = [default_sort_order] * len(sort_columns)

        if len(sort_orders) == 1 and len(sort_columns) > 1:
            sort_orders = sort_orders * len(sort_columns)

        if len(sort_orders) != len(sort_columns):
            raise ValueError("sort_order must match sort_on length")

        return sort_columns, sort_orders

    def _coalesce_nullable_sort_column(
        self,
        col: ColumnElement[Any] | InstrumentedAttribute[Any],
        sort_order: SortOrder,
    ) -> ColumnElement[Any] | InstrumentedAttribute[Any]:
        """Coalesces nullable sort columns so that NULLs land at the boundary
        dictated by the sort direction: first for ASC (nulls_first), last for
        DESC (nulls_last).  Both directions map to -inf / INT_MIN because
        -inf is the minimum value in either direction — it floats to the top
        of an ASC scan and sinks to the bottom of a DESC scan."""
        if not getattr(col, "nullable", False):
            return col

        if isinstance(col.type, Float):
            return func.coalesce(col, float("-inf"))

        if isinstance(col.type, Integer):
            sentinel = -1 if sort_order == SortOrder.DESC else -(2**31)
            return func.coalesce(col, sentinel)

        if isinstance(col.type, String) and not isinstance(col.type, Enum):
            return func.coalesce(col, "")

        if isinstance(col.type, DateTime):
            sentinel = datetime(1970, 1, 1, tzinfo=timezone.utc)
            return func.coalesce(col, sentinel)

        raise NotImplementedError(
            f"Cannot coalesce nullable sort column {col} of type: {col.type}"
        )

    def _coalesce_nullable_cursor_value(
        self,
        column_name: str,
        sort_order: SortOrder,
        value: Any,
    ) -> Any:
        if value is not None:
            return value

        col = (
            self._extra_sort_columns[column_name]
            if column_name in self._extra_sort_columns
            else getattr(self.model, column_name)
        )
        if not getattr(col, "nullable", False):
            return value

        if isinstance(col.type, Float):
            return float("-inf")

        if isinstance(col.type, Integer):
            return -1 if sort_order == SortOrder.DESC else -(2**31)

        if isinstance(col.type, String) and not isinstance(col.type, Enum):
            return ""

        if isinstance(col.type, DateTime):
            return datetime(1970, 1, 1, tzinfo=timezone.utc)

        return value

    def _build_sort_specs(
        self,
        model: "type[BaseModel]",
        sort_on: str | list[str],
        sort_order: SortOrder | list[SortOrder],
    ) -> list[tuple[str, SortOrder]]:
        sort_columns, sort_orders = self.normalise_sort_args(
            sort_on,
            sort_order,
        )
        sort_specs = list(zip(sort_columns, sort_orders, strict=True))

        secondary_sort = SECONDARY_SORTS.get(model.__name__)
        secondary_column = (
            secondary_sort.order_on
            if secondary_sort
            else DEFAULT_SECONDARY_SORT
        )
        secondary_order = (
            secondary_sort.order
            if secondary_sort
            else (sort_specs[0][1] if sort_specs else SortOrder.DESC)
        )

        if secondary_column not in [column for column, _ in sort_specs]:
            sort_specs.append((secondary_column, secondary_order))

        return sort_specs

    def _get_cursor_sort_orders(self) -> list[SortOrder]:
        if self.cursor is None:
            return []

        if self.cursor.sort_orders:
            return self.cursor.sort_orders

        return [self.cursor.sort_order] * len(self.cursor.cursor_values)

    def _get_sort_expression(
        self,
        column_name: str,
        sort_order: SortOrder,
    ) -> ColumnElement[Any] | InstrumentedAttribute[Any]:
        column = (
            self._extra_sort_columns[column_name]
            if column_name in self._extra_sort_columns
            else getattr(self.model, column_name)
        )
        return self._coalesce_nullable_sort_column(column, sort_order)

    def _reverse_sort_orders(
        self,
        sort_order: SortOrder | list[SortOrder],
    ) -> SortOrder | list[SortOrder]:
        if isinstance(sort_order, list):
            return [-order for order in sort_order]

        return -sort_order

    def _build_pagination_query(self) -> Select[Any]:
        """
        Build the inner query based off the input select query that will be used to
        apply pagination to the main query.
        Performs three crucial steps:

        1. Adds a "result_id" column to the results using the dense_rank() window
           function that is used later to limit the number of results returned
        2. Applies the cursor values as a WHERE clause to skip results to the correct
           "page"
        3. Orders the results by the appropriate sorting columns to ensure stable
           sorting
        """
        # First remove any existing order_by clauses that shouldn't be there
        query = self._select_query.order_by(None)

        # Add a dense_rank() window function to the query to get a unique counter of
        # the "primary" model being returned. This is used in the final query to limit
        # the number of results returned.
        query = query.add_columns(
            func.dense_rank()
            .over(order_by=self._get_order_by())
            .label("result_id")
        )

        # If there is a cursor, apply the cursor values as a WHERE clause to skip
        # results to the correct "page"
        if self.cursor:
            cursor = self.cursor
            cursor_orders = self._get_cursor_sort_orders()

            # Build the pagination WHERE clause from the cursor values & sort order
            cols = [
                self._get_sort_expression(col, order)
                for (col, _), order in zip(
                    cursor.cursor_values,
                    cursor_orders,
                    strict=True,
                )
            ]
            vals: list[Any] = [
                self._coalesce_nullable_cursor_value(col, order, val)
                for (col, val), order in zip(
                    cursor.cursor_values,
                    cursor_orders,
                    strict=True,
                )
            ]

            if len(set(cursor_orders)) == 1:
                compare = (
                    operator.lt
                    if cursor_orders[0] == SortOrder.DESC
                    else operator.gt
                )
                query = query.where(compare(tuple_(*cols), tuple_(*vals)))
            else:
                comparisons: list[ColumnElement[bool]] = []
                for index, (col, val, order) in enumerate(
                    zip(cols, vals, cursor_orders, strict=True)
                ):
                    compare = (
                        operator.lt if order == SortOrder.DESC else operator.gt
                    )
                    prefix: list[ColumnElement[bool]] = [
                        cols[prefix_index] == vals[prefix_index]
                        for prefix_index in range(index)
                    ]
                    comparisons.append(and_(*prefix, compare(col, val)))

                query = query.where(or_(*comparisons))

        query = query.order_by(*self._get_order_by())

        return query

    def _get_order_by(self) -> list[ColumnElement[Any]]:
        """
        Helper function to generate the order_by clause for a query accounting for
        whether or not a cursor is provided.

        For columns listed in ``_extra_sort_columns`` the caller-supplied
        ``ColumnElement`` is used directly (with direction applied here) instead
        of routing through ``model.order_by``, which only understands columns that
        are actual attributes of the model.
        """
        order_by: list[ColumnElement[Any]] = []
        # Apply the cursor sort ordering or default ordering if no cursor
        if self.cursor is not None:
            for (col, _), order in zip(
                self.cursor.cursor_values,
                self._get_cursor_sort_orders(),
                strict=True,
            ):
                if col in self._extra_sort_columns:
                    col_expr = self._get_sort_expression(col, order)
                    if order == SortOrder.DESC:
                        order_by.append(col_expr.desc())
                    else:
                        order_by.append(col_expr.asc())
                else:
                    order_by.append(self.model.order_by(col, order))
        else:
            for col, order in self._sort_specs:
                if col in self._extra_sort_columns:
                    col_expr = self._get_sort_expression(col, order)
                    if order == SortOrder.DESC:
                        order_by.append(col_expr.desc())
                    else:
                        order_by.append(col_expr.asc())
                else:
                    order_by.append(self.model.order_by(col, order))

        return order_by

    def _build_query(self) -> None:
        """
        Build the final query that will be executed to get the results we want with all
        ordering, filtering, pagination, and limiting applied.
        The query is made up of two pieces:

        1. Inner query - This takes the input select query with user-specific joins &
           filters and applies pagination logic to it. See `_build_pagination_query()`.
        2. Outer query - This selects the core columns from the inner query and applies
           the limit to return the correct number of results.

        When ``_extra_sort_columns`` is provided the outer query additionally selects
        those extra columns so that their values can be captured during ``_paginate``
        and used for cursor creation.  The extra columns are expected to be labelled
        ``_extra_<logical_name>`` in the inner query (e.g. ``_extra_concern_score``).
        """
        self._pagination_query = self._build_pagination_query()

        # Turn our paginated query into a subquery mapped to the desired model for use
        # as the inner query in the final query.
        subquery = self._pagination_query.subquery()
        alias = aliased(self.model, subquery)
        # Select the core columns from the subquery and limit the number of results
        # using the result_id. We deliberately select limit + 1 results to later
        # determine if there are more results to paginate to.
        if self._extra_sort_columns:
            extra_cols = [
                subquery.c[f"_extra_{col_name}"]
                for col_name in self._extra_sort_columns
            ]
            self.query = (
                select(alias, *extra_cols)
                .select_from(subquery)
                .where(subquery.c.result_id <= self.limit + 1)
                .order_by(subquery.c.result_id)
            )
        else:
            self.query = (
                select(alias)
                .select_from(subquery)
                .where(subquery.c.result_id <= self.limit + 1)
                .order_by(subquery.c.result_id)
            )

    def _get_total_count(self, db: Session) -> None:
        """
        Get the total count of items in the query before pagination & limiting.
        """
        base = (
            self._count_query
            if self._count_query is not None
            else self._select_query
        )
        self._total_count_query = (
            base.with_only_columns(func.count(distinct(self.model.uid)))
            .order_by(None)
            .limit(None)
        )

        start_time = time.time()
        self.total_count = db.scalar(self._total_count_query) or 0
        self.count_time = time.time() - start_time

    def _paginate(self, db: Session) -> "Paginator":
        """
        Executes the built query and inspects the results to determine subsequent
        cursors and pagination metadata.

        When ``_extra_sort_columns`` is present the query returns rows that include
        both the ORM object and extra column values.  ``db.execute()`` is used in
        that case so that the extra values can be captured for cursor creation.
        """
        start_time = time.time()

        if self._extra_sort_columns:
            raw_rows = db.execute(self.query).all()
            self.query_time = time.time() - start_time

            page_rows = raw_rows[: self.limit]
            self._has_more = bool(raw_rows[self.limit :])

            extra_col_names = list(self._extra_sort_columns.keys())
            self.results = [row[0] for row in page_rows]
            self._extra_values_by_uid = {
                str(row[0].uid): {
                    col_name: row[i + 1]
                    for i, col_name in enumerate(extra_col_names)
                }
                for row in page_rows
            }
        else:
            rows = db.scalars(self.query).unique().all()
            self.query_time = time.time() - start_time

            self.results, self._has_more = (
                rows[: self.limit],
                bool(rows[self.limit :]),
            )

        # Not to be confused with sort_order. Needed to paginate backwards using
        # `prev_cursor` while still maintaining the specified sort order.
        if self._reverse:
            self.results = self.results[::-1]

        self.count = len(self.results)

        self.get_next_cursor()
        self.get_prev_cursor()

        return self

    def get_next_cursor(self) -> PaginationCursor | None:
        """
        Get the cursor for the next page of results based on the last item.
        If a cursor is already in use, re-use the cursor values to maintain stable sorting.
        """
        if not self.results:
            return None

        # If not navigating backward and no more results exist, we're at the end
        if not self._has_more and not self._reverse:
            return None

        next_item = self.results[-1]
        extra_values = self._extra_values_by_uid.get(str(next_item.uid))

        if self.next_cursor is None:
            if self.cursor is None:
                self.next_cursor = PaginationCursor.create_cursor(
                    next_item,
                    sort_on=[column for column, _ in self._sort_specs],
                    sort_order=[order for _, order in self._sort_specs],
                    sort_alias=self.sort_alias,
                    extra_values=extra_values,
                )
            else:
                self.next_cursor = PaginationCursor.create_cursor(
                    next_item,
                    from_cursor=self.cursor,
                    sort_alias=self.sort_alias,
                    sort_order=self._reverse_sort_orders(
                        self._get_cursor_sort_orders()
                    )
                    if self._reverse
                    else self._get_cursor_sort_orders(),
                    extra_values=extra_values,
                )
        return self.next_cursor

    def get_prev_cursor(self) -> PaginationCursor | None:
        """
        Get the cursor for the previous page of results based on the first item.
        If there is no current cursor, return None as we must be on page 1.
        If a cursor is already in use, re-use the cursor values to maintain stable sorting.
        """
        if self.cursor is None:
            return None

        if not self.results:
            return None

        # If navigating backward and no more results exist, we're at page 1
        if self._reverse and not self._has_more:
            return None

        prev_item = self.results[0]
        extra_values = self._extra_values_by_uid.get(str(prev_item.uid))

        if self.prev_cursor is None:
            self.prev_cursor = PaginationCursor.create_cursor(
                prev_item,
                from_cursor=self.cursor,
                sort_order=self._get_cursor_sort_orders()
                if self._reverse
                else self._reverse_sort_orders(self._get_cursor_sort_orders()),
                sort_alias=self.sort_alias,
                extra_values=extra_values,
            )
        return self.prev_cursor
