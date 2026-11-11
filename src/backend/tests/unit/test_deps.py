from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from src.backend.app import deps
from src.backend.app.access import SafeSession
from src.backend.app.api.v1 import organisation
from src.backend.app.schemas.organisation import OrganisationDB
from src.backend.app.schemas.user import User
from src.backend.app.util import context


def test_current_user(test_user: User, monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(HTTPException):
        deps.current_user()

    with monkeypatch.context() as _m:
        _m.setattr(context, "get_current_user", lambda: test_user)
        assert deps.current_user() == test_user


def test_current_org(
    test_org: OrganisationDB,
    monkeypatch: pytest.MonkeyPatch,
    test_admin_session: SafeSession,
):
    mock_get_orgs = MagicMock(return_value=None)

    with (
        monkeypatch.context() as _m,
        pytest.raises(HTTPException),
    ):
        _m.setattr(organisation, "get_organisation", mock_get_orgs)
        deps.current_org(test_admin_session, str(test_org.uid))
        mock_get_orgs.assert_called_once()

    mock_get_orgs.reset_mock()

    mock_get_orgs.return_value = test_org
    with monkeypatch.context() as _m:
        _m.setattr(organisation, "get_organisation", mock_get_orgs)
        assert (
            deps.current_org(test_admin_session, str(test_org.uid)) == test_org
        )
        mock_get_orgs.assert_called_once()
        assert context.get_current_org() == test_org


def test_current_org_rejects_non_uuid(
    test_admin_session: SafeSession,
):
    with pytest.raises(HTTPException) as exc_info:
        deps.current_org(test_admin_session, "not-a-uuid")
    assert exc_info.value.status_code == 400
