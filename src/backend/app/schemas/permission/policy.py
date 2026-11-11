from collections.abc import Sequence

from pydantic import Field, model_validator
from src.backend.app.schemas.base import PydanticSchema
from src.backend.app.schemas.permission.condition import Condition
from src.backend.app.schemas.permission.resource_type import ResourceType
from src.backend.app.schemas.permission.role import Role


class Policy(PydanticSchema):
    resource_type: ResourceType = Field(alias="resource-type")
    roles: set[Role]
    actions: set[str]
    condition: Condition

    @model_validator(mode="after")
    def check_resource_type(self):
        action_resource_types = {
            action.split(":")[1] for action in self.actions
        }
        if action_resource_types != {self.resource_type}:
            raise ValueError(
                f"Actions {self.actions} do not match the policy resource type '{self.resource_type}'"
            )

        if not self.condition.is_valid_with_resource_type(self.resource_type):
            raise ValueError(
                f"Condition {self.condition} is not valid with policy resource type '{self.resource_type}'"
            )

        return self

    def applies_to_user_roles(self, user_roles: Sequence[str]) -> bool:
        return any(role in self.roles for role in user_roles)

    def applies_to_action(self, action: str) -> bool:
        return action in self.actions
