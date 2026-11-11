from unittest.mock import MagicMock

import pytest
from fastapi import Response
from src.backend.app.schemas.response import CommonResponseHeaders
from src.backend.app.util.enums import SortOrder
from src.backend.app.util.pagination import PaginationCursor, Paginator
from src.backend.app.util.pagination_headers import set_pagination_headers

NEXT_CURSOR = PaginationCursor(
    cursor_values=[("created_at", "2024-01-02T00:00:00+00:00")],
    sort_order=SortOrder.DESC,
)
PREV_CURSOR = PaginationCursor(
    cursor_values=[("created_at", "2024-01-01T00:00:00+00:00")],
    sort_order=SortOrder.ASC,
)


def make_paginator(
    next_cursor: PaginationCursor | None,
    prev_cursor: PaginationCursor | None,
    total_count: int | None,
) -> MagicMock:
    paginator = MagicMock(spec=Paginator)
    paginator.next_cursor = next_cursor
    paginator.prev_cursor = prev_cursor
    paginator.total_count = total_count
    return paginator


def set_headers_inline(response: Response, paginator: MagicMock) -> None:
    """The inline block the helper replaces, kept here as the reference."""
    headers = CommonResponseHeaders.model_validate(
        {
            "next_cursor": paginator.next_cursor,
            "prev_cursor": paginator.prev_cursor,
            "total": paginator.total_count,
        }
    )
    response.headers.update(headers.model_dump(by_alias=True))


def test_set_pagination_headers():
    response = Response()
    paginator = make_paginator(NEXT_CURSOR, PREV_CURSOR, 42)

    set_pagination_headers(response, paginator)

    assert response.headers["natcap-next-cursor"] == NEXT_CURSOR.model_dump()
    assert response.headers["natcap-prev-cursor"] == PREV_CURSOR.model_dump()
    assert response.headers["natcap-total-count"] == "42"


def test_set_pagination_headers_none_values():
    response = Response()
    paginator = make_paginator(None, None, None)

    set_pagination_headers(response, paginator)

    assert response.headers["natcap-next-cursor"] == ""
    assert response.headers["natcap-prev-cursor"] == ""
    assert response.headers["natcap-total-count"] == ""


@pytest.mark.parametrize(
    "next_cursor, prev_cursor, total_count",
    [
        (NEXT_CURSOR, PREV_CURSOR, 42),
        (NEXT_CURSOR, None, 0),
        (None, PREV_CURSOR, 7),
        (None, None, None),
    ],
)
def test_set_pagination_headers_matches_inline_block(
    next_cursor: PaginationCursor | None,
    prev_cursor: PaginationCursor | None,
    total_count: int | None,
):
    paginator = make_paginator(next_cursor, prev_cursor, total_count)
    helper_response = Response()
    inline_response = Response()

    set_pagination_headers(helper_response, paginator)
    set_headers_inline(inline_response, paginator)

    assert helper_response.raw_headers == inline_response.raw_headers
