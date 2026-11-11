import contextlib
from typing import NewType

from pydantic import UUID4
from sqlalchemy.orm import Session
from src.backend.app.config import settings
from src.backend.app.database import DatabaseFactory
from src.backend.app.schemas.permission.policy_document import (
    PolicyDocument,
)
from src.backend.app.schemas.user import User

logger = settings.logger


SafeSession = NewType("SafeSession", Session)
"""
An SQLAlchemy Session handed out by an `Access` instance. Every service
function takes one of these rather than a bare Session so that the only way
to reach the database from a request is through the user's `Access`.
"""


class Access:
    """Role-based access control checks for one user against the policy
    document."""

    def __init__(
        self,
        policy_document: PolicyDocument,
        user: User,
        database_factory: DatabaseFactory,
    ):
        self.policy_document = policy_document
        self.user = user
        self.database_factory = database_factory

    def check(self, action: str, resource_uid: str | UUID4 | None) -> bool:
        """
        Returns true if the user has access to perform `action` on `resource_uid`.
        """
        return any(
            policy.condition.applies_to(self.user, resource_uid)
            for policy in self.policy_document.policies
            if policy.applies_to_user_roles(self.user.roles)
            and policy.applies_to_action(action)
        )

    def get_actions(
        self, resource_type: str, resource_uid: UUID4 | None
    ) -> list[str]:
        return sorted(
            {
                action
                for policy in self.policy_document.policies
                if policy.applies_to_user_roles(self.user.roles)
                and policy.resource_type == resource_type
                and policy.condition.applies_to(self.user, resource_uid)
                for action in policy.actions
            }
        )

    @contextlib.contextmanager
    def get_session(self):
        """Provides an SQLAlchemy session for this user's requests."""
        with self.database_factory.session_factory() as session:
            yield SafeSession(session)
