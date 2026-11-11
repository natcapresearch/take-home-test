from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import CascadeOptions
from src.backend.app.database import Session
from src.backend.app.models.organisation import Organisation, OrganisationMixin
from src.backend.app.schemas.organisation import OrganisationDB


def test_organisation(
    set_up_test_db: None, test_db_session: Session, test_org: OrganisationDB
):
    session = test_db_session
    session.add(Organisation(**test_org.model_dump()))
    org_orm = session.query(Organisation).first()
    assert org_orm is not None

    assert org_orm.uid == test_org.uid
    assert org_orm.name == test_org.name
    assert isinstance(org_orm.authorised_email_domains, list)
    assert org_orm.authorised_email_domains == test_org.authorised_email_domains
    assert org_orm.config == test_org.config

    org = OrganisationDB.model_validate(org_orm)
    assert org == test_org


def test_delete_cascade(set_up_test_db: None):
    """
    Organisation deletes should cascade to models which reference them, and use passive
    deletes, so that removing an organisation never leaves orphaned rows behind.
    """
    org_relationships: list[Any] = [
        relationship[1]
        for relationship in inspect(Organisation).relationships.items()  # type: ignore
        if issubclass(relationship[1].mapper.class_, OrganisationMixin)  # type: ignore
    ]
    assert org_relationships
    for relationship in org_relationships:
        assert relationship.passive_deletes
        assert relationship.cascade == CascadeOptions.from_string(  # type: ignore
            "all, delete-orphan"
        )
