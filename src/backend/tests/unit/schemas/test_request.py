import pytest
from src.backend.app.schemas import request as request_schemas
from src.backend.app.schemas.request import (
    ChangeSetsQueryParams,
    ChangeSetUpdate,
    CommonQueryParams,
)
from src.backend.app.util.enums import ChangeSetState, SortOrder
from src.backend.app.util.pagination import PaginationCursor, PaginationError


def test_common_query_params_defaults():
    params = CommonQueryParams()
    assert params.sort_on is None
    assert params.sort_order == SortOrder.DESC
    assert params.before is None
    assert params.after is None


def test_common_query_params_empty_cursor_is_none():
    params = CommonQueryParams.model_validate({"before": "", "after": ""})
    assert params.before is None
    assert params.after is None


def test_common_query_params_logs_when_cursor_and_sort_on_provided(monkeypatch):
    debug = []
    monkeypatch.setattr(
        request_schemas.logger, "debug", lambda msg: debug.append(msg)
    )

    CommonQueryParams(
        before=PaginationCursor(cursor_values=[("name", "a")]),
        sort_on="name",
    )

    assert debug == ["After/before cursor will take precedence over sort_on"]


def test_common_query_params_before_and_after_raises_pagination_error():
    with pytest.raises(
        PaginationError, match="Cannot specify both before and after cursors"
    ):
        CommonQueryParams(
            before=PaginationCursor(cursor_values=[("name", "a")]),
            after=PaginationCursor(cursor_values=[("name", "b")]),
        )


def test_change_sets_query_params_state():
    assert ChangeSetsQueryParams().state is None
    assert (
        ChangeSetsQueryParams(state="published").state
        == ChangeSetState.PUBLISHED
    )


def test_change_set_update_all_fields_optional():
    body = ChangeSetUpdate()
    assert body.name is None
    assert body.description is None
    assert body.state is None

    with pytest.raises(ValueError, match="state"):
        ChangeSetUpdate(state="archived")  # type: ignore[arg-type]
