import pytest
from pydantic import ValidationError
from src.backend.app.schemas.permission.condition import Unconditional
from src.backend.app.schemas.permission.policy_document import PolicyDocument
from src.backend.app.schemas.permission.policy_document import (
    policy_document as production_policy_document,
)


def test_policy_document_parse_smoke_test():
    assert production_policy_document
    assert len(production_policy_document.policies) == 4
    for policy in production_policy_document.policies:
        assert policy.roles
        assert policy.actions
        assert isinstance(policy.condition, Unconditional)


def test_policy_document_grants_expected_actions():
    def actions(role: str, resource_type: str) -> set[str]:
        return {
            action
            for policy in production_policy_document.policies
            if policy.applies_to_user_roles([role])
            and policy.resource_type == resource_type
            for action in policy.actions
        }

    assert actions("admin", "change_set") == {
        "read:change_set:basic",
        "read:change_set:all",
        "update:change_set:basic",
        "update:change_set:publish",
    }
    assert actions("viewer", "change_set") == {"read:change_set:basic"}
    assert (
        actions("admin", "org")
        == actions("viewer", "org")
        == {"read:org:basic"}
    )
    assert (
        actions("admin", "common")
        == actions("viewer", "common")
        == {"read:common:basic"}
    )


def test_policy_document_parses_from_yaml():
    policy_document = PolicyDocument.from_yaml("""
policies:
  - resource-type: org
    roles:
      - admin
    actions:
      - read:org:basic
    condition: unconditional
        """)
    assert len(policy_document.policies) == 1

    assert policy_document.policies[0].condition.name == "unconditional"
    assert policy_document.policies[0].roles == {"admin"}
    assert policy_document.policies[0].actions == {"read:org:basic"}


def test_policy_document_parse_rejects_bad_yaml():
    with pytest.raises(ValidationError, match="Field required"):
        PolicyDocument.from_yaml("""
policies:
  - resuource-type: org
    r0les:
      - unknown-role
    permissions:
      - read:org:basic
    conditiun: unconditional
        """)


def test_policy_document_parse_rejects_unknown_role():
    with pytest.raises(ValidationError, match="roles"):
        PolicyDocument.from_yaml("""
policies:
  - resource-type: org
    roles:
      - superuser
    actions:
      - read:org:basic
    condition: unconditional
        """)


def test_policy_document_parse_rejects_mismatched_actions():
    with pytest.raises(
        ValidationError,
        match=r"Actions {'create:org:basic'} do not match the policy resource type 'change_set'",
    ):
        PolicyDocument.from_yaml("""
policies:
  - resource-type: change_set
    roles:
      - admin
    actions:
      - create:org:basic
    condition: unconditional
        """)


def test_policy_document_parse_rejects_unknown_condition():
    with pytest.raises(
        ValidationError, match="Could not find condition 'super:cool'"
    ):
        PolicyDocument.from_yaml("""
policies:
  - resource-type: org
    roles:
      - admin
    actions:
      - read:org:basic
    condition: super:cool
        """)
