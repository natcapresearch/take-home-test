from unittest.mock import MagicMock

import pytest
from sqlalchemy import nullsfirst, nullslast, select
from sqlalchemy.orm import Session
from src.backend.app.config import settings
from src.backend.app.models.base import BaseModel
from src.backend.app.models.change_set import ChangeSet
from src.backend.app.util import pagination
from src.backend.app.util.enums import SortOrder

logger = settings.logger


def test_paginate_none(monkeypatch: pytest.MonkeyPatch):
    mock_paginator = MagicMock(spec=pagination.Paginator)

    with monkeypatch.context() as _m:
        _m.setattr(pagination, "Paginator", mock_paginator)
        ChangeSet.paginate(
            MagicMock(spec=Session),
            select(ChangeSet),
            None,
            10,
        )
        mock_paginator.assert_called_once()


def test_paginate_cursor(monkeypatch: pytest.MonkeyPatch):
    mock_paginator = MagicMock(spec=pagination.Paginator)

    with monkeypatch.context() as _m:
        _m.setattr(pagination, "Paginator", mock_paginator)
        ChangeSet.paginate(
            MagicMock(spec=Session),
            select(ChangeSet),
            pagination.PaginationCursor(
                cursor_values=[("created_at", 1), ("uid", 2)]
            ),
            10,
        )
        mock_paginator.assert_called_once()


def test_paginate_sort_on(monkeypatch: pytest.MonkeyPatch):
    mock_paginator = MagicMock(spec=pagination.Paginator)

    with monkeypatch.context() as _m:
        _m.setattr(pagination, "Paginator", mock_paginator)
        ChangeSet.paginate(
            MagicMock(spec=Session),
            select(ChangeSet).order_by(
                ChangeSet.order_by("created_at", SortOrder.DESC)
            ),
            None,
            10,
        )
        mock_paginator.assert_called_once()


def test_paginate_both(monkeypatch: pytest.MonkeyPatch):
    mock_paginator = MagicMock(spec=pagination.Paginator)

    with monkeypatch.context() as _m:
        _m.setattr(pagination, "Paginator", mock_paginator)
        ChangeSet.paginate(
            MagicMock(spec=Session),
            select(ChangeSet).order_by(
                ChangeSet.order_by("updated_at", SortOrder.ASC)
            ),
            pagination.PaginationCursor(
                cursor_values=[("created_at", 1), ("uid", 2)]
            ),
            10,
        )
        mock_paginator.assert_called_once()


def test_order_by(mock_model: type[BaseModel]):
    a_model = mock_model()

    with pytest.raises(ValueError):
        a_model.order_by("uid", "not_an_order")  # type: ignore

    order = a_model.order_by(None, SortOrder.ASC)  # type: ignore
    assert str(order) == str(nullsfirst(mock_model.created_at.asc()))

    with pytest.raises(AttributeError):
        a_model.order_by("not_a_column", SortOrder.ASC)

    order = a_model.order_by("uid", SortOrder.ASC)
    assert str(order) == str(nullsfirst(mock_model.uid.asc()))

    order = a_model.order_by("uid", SortOrder.DESC)
    assert str(order) == str(nullslast(mock_model.uid.desc()))


def test___repr__(mock_model: BaseModel):
    a_model = mock_model()
    assert repr(a_model)
