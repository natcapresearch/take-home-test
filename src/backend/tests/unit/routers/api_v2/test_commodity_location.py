import uuid
from unittest.mock import MagicMock

import pytest
from src.backend.app.main import app
from src.backend.app.routers.api_v2 import (
    commodity_location as commodity_location_router_module,
)
from src.backend.app.util import change_set as change_set_util
from src.backend.app.util.enums import EntityScope, SortOrder
from src.backend.app.util.pagination import PaginationCursor, Paginator
from src.backend.conftest import ClientGetter


@pytest.fixture(autouse=True)
def _visible_change_set(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """These routes call get_visible_change_set_or_404 first; its own rules
    are tested in tests/unit/util/test_change_set.py. Here every change set
    is visible."""
    mock = MagicMock()
    monkeypatch.setattr(change_set_util, "get_visible_change_set_or_404", mock)
    return mock


def _empty_page() -> MagicMock:
    return MagicMock(
        return_value=(
            [],
            MagicMock(
                spec=Paginator,
                next_cursor=None,
                prev_cursor=None,
                total_count=0,
            ),
        )
    )


def _cursor(*pairs: tuple[str, str]) -> str:
    """A well-formed cursor, serialised the way the API returns one."""
    return PaginationCursor(cursor_values=list(pairs)).model_dump()


def test_get_commodity_sources_api_v2_defaults_and_pagination_headers(
    get_client: ClientGetter,
    monkeypatch: pytest.MonkeyPatch,
):
    mock_get_sources = _empty_page()
    with get_client(app) as client, monkeypatch.context() as _m:
        _m.setattr(
            commodity_location_router_module.commodity_location_api_v2,
            "get_commodity_sources",
            mock_get_sources,
        )

        res = client.get(
            "/api/v2/commodity-sources/",
            params={"change_set_uid": str(uuid.uuid4())},
        )

    assert res.status_code == 200
    kwargs = mock_get_sources.call_args.kwargs
    assert kwargs["sort_on"] == "identifier"
    assert kwargs["sort_order"] == SortOrder.DESC
    assert res.headers["natcap-total-count"] == "0"


@pytest.mark.parametrize(
    "sort_on",
    ["sourcing_country", "sourcing_region", "supplier", "product", "spend"],
)
def test_get_commodity_sources_api_v2_accepts_canonical_sort_keys(
    get_client: ClientGetter,
    monkeypatch: pytest.MonkeyPatch,
    sort_on: str,
):
    mock_get_sources = _empty_page()
    with get_client(app) as client, monkeypatch.context() as _m:
        _m.setattr(
            commodity_location_router_module.commodity_location_api_v2,
            "get_commodity_sources",
            mock_get_sources,
        )

        res = client.get(
            "/api/v2/commodity-sources/",
            params={"change_set_uid": str(uuid.uuid4()), "sort_on": sort_on},
        )

    assert res.status_code == 200
    assert mock_get_sources.call_args.kwargs["sort_on"] == sort_on


@pytest.mark.parametrize(
    "sort_on",
    [
        "sourcing_country_name",
        "sourcing_administrative_level_1_name",
        "supplier_name",
        "product_name",
        "no_such_column",
    ],
)
def test_get_commodity_sources_api_v2_rejects_non_canonical_sort_keys(
    get_client: ClientGetter,
    monkeypatch: pytest.MonkeyPatch,
    sort_on: str,
):
    mock_get_sources = _empty_page()
    with get_client(app) as client, monkeypatch.context() as _m:
        _m.setattr(
            commodity_location_router_module.commodity_location_api_v2,
            "get_commodity_sources",
            mock_get_sources,
        )

        res = client.get(
            "/api/v2/commodity-sources/",
            params={"change_set_uid": str(uuid.uuid4()), "sort_on": sort_on},
        )

    assert res.status_code == 422
    mock_get_sources.assert_not_called()


@pytest.mark.parametrize(
    ("cursor_params", "detail"),
    [
        ({"after": "not-a-cursor"}, "Failed to deserialise cursor"),
        (
            {
                "before": _cursor(("identifier", "a")),
                "after": _cursor(("identifier", "b")),
            },
            "Cannot specify both before and after cursors",
        ),
    ],
    ids=["malformed-cursor", "before-and-after"],
)
def test_get_commodity_sources_api_v2_rejects_invalid_cursors_with_422(
    get_client: ClientGetter,
    monkeypatch: pytest.MonkeyPatch,
    cursor_params: dict[str, str],
    detail: str,
):
    """A bad cursor is a bad request param, so 422 like any other, not an
    unhandled PaginationError and a 500."""
    mock_get_sources = _empty_page()
    with get_client(app) as client, monkeypatch.context() as _m:
        _m.setattr(
            commodity_location_router_module.commodity_location_api_v2,
            "get_commodity_sources",
            mock_get_sources,
        )

        res = client.get(
            "/api/v2/commodity-sources/",
            params={"change_set_uid": str(uuid.uuid4()), **cursor_params},
        )

    assert res.status_code == 422, res.text
    assert res.json()["detail"] == detail
    mock_get_sources.assert_not_called()


def test_get_commodity_summary_api_v2_passes_scope(
    get_client: ClientGetter,
    monkeypatch: pytest.MonkeyPatch,
):
    mock_get_summary = MagicMock(
        return_value={
            "total_commodities": 0,
            "total_suppliers": 0,
            "total_locations": 0,
            "total_spend": None,
            "total_quantity": None,
        }
    )
    with get_client(app) as client, monkeypatch.context() as _m:
        _m.setattr(
            commodity_location_router_module.commodity_location_api_v2,
            "get_commodity_summary",
            mock_get_summary,
        )

        res = client.get(
            "/api/v2/commodity-summary/",
            params={"change_set_uid": str(uuid.uuid4()), "scope": "all"},
        )

    assert res.status_code == 200, res.text
    assert mock_get_summary.call_args.args[3] == EntityScope.ALL


def test_get_aggregated_commodity_regions_api_v2_passes_flags(
    get_client: ClientGetter,
    monkeypatch: pytest.MonkeyPatch,
):
    mock_get_regions = MagicMock(return_value=[])
    with get_client(app) as client, monkeypatch.context() as _m:
        _m.setattr(
            commodity_location_router_module.commodity_location_api_v2,
            "get_aggregated_commodity_regions",
            mock_get_regions,
        )

        res = client.get(
            "/api/v2/commodity-source-regions-aggregated/",
            params={
                "change_set_uid": str(uuid.uuid4()),
                "commodity_subgroups": ["Coffee"],
                "include_geometry": "true",
                "group_by_country": "true",
            },
        )

    assert res.status_code == 200, res.text
    assert res.json() == []
    kwargs = mock_get_regions.call_args.kwargs
    assert kwargs["commodity_subgroups"] == ["Coffee"]
    assert kwargs["include_geometry"] is True
    assert kwargs["group_by_country"] is True
