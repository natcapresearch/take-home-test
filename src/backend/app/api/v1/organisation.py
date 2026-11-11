from uuid import UUID

from pydantic import UUID4
from sqlalchemy import select
from src.backend.app.access import SafeSession
from src.backend.app.config import settings
from src.backend.app.models.change_set import ChangeSet
from src.backend.app.models.organisation import Organisation
from src.backend.app.schemas.organisation import OrganisationDB
from src.backend.app.util.enums import ChangeSetState

logger = settings.logger


def _get_latest_non_draft_change_set_uid(
    safe_session: SafeSession, org_uid: UUID4
) -> UUID | None:
    return safe_session.execute(
        select(ChangeSet.uid)
        .where(ChangeSet.org_uid == org_uid)
        .where(ChangeSet.state != ChangeSetState.DRAFT)
        .order_by(
            ChangeSet.created_at.desc(),
            ChangeSet.uid.desc(),
        )
        .limit(1)
    ).scalar_one_or_none()


def _set_default_change_set_uid(
    safe_session: SafeSession, org_db: OrganisationDB, is_admin: bool = False
) -> None:
    if not is_admin:
        return

    # Admins always see the most recent non-DRAFT changeset in-memory,
    # overriding whatever the DB persisted (which tracks newest PUBLISHED).
    newest_non_draft = _get_latest_non_draft_change_set_uid(
        safe_session, org_db.uid
    )
    if newest_non_draft is not None:
        org_db.default_change_set_uid = newest_non_draft


def get_organisation(
    safe_session: SafeSession,
    org_uid: UUID4,
    is_admin: bool = False,
) -> OrganisationDB | None:
    """Returns a single org by uid, or None when it does not exist."""
    org_orm = safe_session.get(Organisation, org_uid)
    if org_orm is None:
        logger.debug(f"Couldn't find organisation {org_uid}")
        return None

    org_db = OrganisationDB.model_validate(org_orm)
    _set_default_change_set_uid(safe_session, org_db, is_admin=is_admin)

    return org_db
