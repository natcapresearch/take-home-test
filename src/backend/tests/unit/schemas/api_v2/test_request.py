import uuid
from typing import Literal

import pytest
from pydantic import ValidationError
from src.backend.app.config import settings
from src.backend.app.schemas.api_v2.request import ChangeSetListQueryParams
from src.backend.app.util.enums import SortOrder
from src.backend.app.util.pagination import PaginationCursor, PaginationError


class _NameSortQueryParams(ChangeSetListQueryParams):
    sort_on: Literal["name", "slug"] = "name"
    sort_order: SortOrder = SortOrder.ASC


def test_change_set_list_query_params_requires_change_set_uid():
    with pytest.raises(ValidationError, match="change_set_uid"):
        ChangeSetListQueryParams.model_validate({})


def test_change_set_list_query_params_declares_no_sort_fields():
    assert "sort_on" not in ChangeSetListQueryParams.model_fields
    assert "sort_order" not in ChangeSetListQueryParams.model_fields


def test_change_set_list_query_params_limit():
    params = ChangeSetListQueryParams(change_set_uid=uuid.uuid4())
    assert params.limit == settings.DEFAULT_PAGE_SIZE

    params = ChangeSetListQueryParams(
        change_set_uid=uuid.uuid4(), limit=settings.MAX_PAGE_SIZE
    )
    assert params.limit == settings.MAX_PAGE_SIZE

    for limit in (0, settings.MAX_PAGE_SIZE + 1):
        with pytest.raises(ValidationError, match="limit"):
            ChangeSetListQueryParams(change_set_uid=uuid.uuid4(), limit=limit)


def test_change_set_list_query_params_before_and_after_raises():
    with pytest.raises(
        PaginationError, match="Cannot specify both before and after cursors"
    ):
        ChangeSetListQueryParams(
            change_set_uid=uuid.uuid4(),
            before=PaginationCursor(cursor_values=[("name", "a")]),
            after=PaginationCursor(cursor_values=[("name", "b")]),
        )


def test_change_set_list_query_params_empty_cursor_is_none():
    params = ChangeSetListQueryParams.model_validate(
        {"change_set_uid": uuid.uuid4(), "before": "", "after": ""}
    )
    assert params.before is None
    assert params.after is None


def test_change_set_list_query_params_subclass_sort_defaults():
    params = _NameSortQueryParams(change_set_uid=uuid.uuid4())
    assert params.sort_on == "name"
    assert params.sort_order == SortOrder.ASC

    params = _NameSortQueryParams(
        change_set_uid=uuid.uuid4(), sort_on="slug", sort_order=SortOrder.DESC
    )
    assert params.sort_on == "slug"
    assert params.sort_order == SortOrder.DESC

    with pytest.raises(ValidationError, match="sort_on"):
        _NameSortQueryParams.model_validate(
            {"change_set_uid": uuid.uuid4(), "sort_on": "foo"}
        )
