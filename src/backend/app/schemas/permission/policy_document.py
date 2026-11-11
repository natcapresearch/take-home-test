from pathlib import Path
from typing import Self

import yaml
from src.backend.app.schemas.base import PydanticSchema
from src.backend.app.schemas.permission.policy import Policy


class PolicyDocument(PydanticSchema):
    policies: list[Policy]

    @classmethod
    def from_yaml(cls, str_: str) -> Self:
        return cls.model_validate(yaml.safe_load(str_))


with Path.open(Path("src/backend/app/policy_document.yaml")) as f:
    policy_document = PolicyDocument.from_yaml(f.read())
