"""`get_change_summary`.

Groups the entities alive as of the change set by their changeset-current
`ExportedCommodityLocation` row.
"""

import uuid
from collections.abc import Callable

import pytest
from src.backend.app.access import SafeSession
from src.backend.app.api.v1.change_set import get_change_summary
from src.backend.app.models.change_set import Change, ChangeSet
from src.backend.app.models.commodity_location_entity import (
    CommodityLocationEntity,
)
from src.backend.app.models.export.exported_commodity_location import (
    ExportedCommodityLocation,
)
from src.backend.app.models.organisation import Organisation
from src.backend.app.schemas.organisation import (
    OrganisationDB,
)
from src.backend.app.util.enums import ChangeSetState, UnitOfAnalysis


@pytest.fixture
def versioned_org_uid(
    make_org_orm: Callable[..., Organisation],
) -> uuid.UUID:
    org = OrganisationDB(
        name="Versioned Summary Org",
        authorised_email_domains=["versioned-summary.com"],
    )
    make_org_orm(org)
    return org.uid


@pytest.fixture
def other_org_uid(
    make_org_orm: Callable[..., Organisation],
) -> uuid.UUID:
    return make_org_orm().uid


def _change_set(
    session: SafeSession,
    org_uid: uuid.UUID,
    parent_uid: uuid.UUID | None = None,
) -> ChangeSet:
    cs = ChangeSet(
        org_uid=org_uid,
        parent_uid=parent_uid,
        state=ChangeSetState.DONE,
        name="Version",
        description="Version description",
    )
    session.add(cs)
    session.flush()
    return cs


def _record(
    session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
    model_type: str,
    *,
    new_uid: uuid.UUID | None = None,
    previous_uid: uuid.UUID | None = None,
) -> None:
    session.add(
        Change(
            org_uid=org_uid,
            change_set_uid=change_set_uid,
            model_type=model_type,
            new_uid=new_uid,
            previous_uid=previous_uid,
            description="test change",
        )
    )
    session.flush()


def _commodity(
    session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
    identifier: str,
    *,
    commodity_type: str,
    country: str | None,
    admin_1: str | None,
    supplier: str | None,
    product: str | None,
) -> CommodityLocationEntity:
    """An alive CommodityLocationEntity plus its current exported row."""
    entity = CommodityLocationEntity(
        org_uid=org_uid,
        identifier=identifier,
        commodity_type=commodity_type,
        commodity_subgroup="subgroup",
        commodity_code="CODE",
        year_purchased=2024,
        supplier=supplier,
        product=product,
        normalised_key=identifier.lower(),
    )
    session.add(entity)
    session.flush()
    _record(
        session,
        org_uid,
        change_set_uid,
        CommodityLocationEntity.__tablename__,
        new_uid=entity.uid,
    )

    exported = ExportedCommodityLocation(
        org_uid=org_uid,
        entity_uid=entity.uid,
        identifier=identifier,
        commodity_type=commodity_type,
        commodity_subgroup="subgroup",
        commodity_code="CODE",
        year_purchased=2024,
        sourcing_country_name=country,
        sourcing_administrative_level_1_name=admin_1,
        supplier=supplier,
        product=product,
    )
    session.add(exported)
    session.flush()
    _record(
        session,
        org_uid,
        change_set_uid,
        ExportedCommodityLocation.__tablename__,
        new_uid=exported.uid,
    )
    return entity


def _texts(summaries: list) -> set[str]:
    return {item.text for item in summaries}


def test_versioned_summary_groups_commodities(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    versioned_org_uid: uuid.UUID,
):
    cs = _change_set(test_admin_session, versioned_org_uid)

    _commodity(
        test_admin_session,
        versioned_org_uid,
        cs.uid,
        "COMMOD 1",
        commodity_type="Arabica",
        country="Brazil",
        admin_1="Minas Gerais",
        supplier="Supplier A",
        product="Product A",
    )
    _commodity(
        test_admin_session,
        versioned_org_uid,
        cs.uid,
        "COMMOD 2",
        commodity_type="Robusta",
        country="Vietnam",
        admin_1=None,
        supplier="Supplier B",
        product="Product B",
    )

    summary = get_change_summary(
        test_admin_session,
        org_uid=versioned_org_uid,
        change_set_uid=cs.uid,
    )

    assert summary.name == "Version"
    assert summary.description == "Version description"
    assert summary.state == ChangeSetState.DONE

    commodities = summary.unit_of_analysis_summaries[
        UnitOfAnalysis.COMMODITY_SOURCE
    ]
    assert _texts(commodities.commodities) == {"Arabica", "Robusta"}
    # "Country Admin1" when admin 1 is present, bare country when it isn't.
    assert _texts(commodities.regions) == {"Brazil Minas Gerais", "Vietnam"}
    assert _texts(commodities.suppliers) == {"Supplier A", "Supplier B"}
    assert _texts(commodities.products) == {"Product A", "Product B"}

    # `value` is a share of the rows, not a count.
    assert {item.value for item in commodities.regions} == {0.5}


def test_versioned_summary_inherits_from_parent_chain(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    versioned_org_uid: uuid.UUID,
):
    """A version that changed nothing still contains everything its
    ancestors put there."""
    parent = _change_set(test_admin_session, versioned_org_uid)
    _commodity(
        test_admin_session,
        versioned_org_uid,
        parent.uid,
        "Inherited",
        commodity_type="Arabica",
        country="Brazil",
        admin_1=None,
        supplier="Supplier A",
        product="Product A",
    )

    child = _change_set(
        test_admin_session, versioned_org_uid, parent_uid=parent.uid
    )

    summary = get_change_summary(
        test_admin_session,
        org_uid=versioned_org_uid,
        change_set_uid=child.uid,
    )

    commodities = summary.unit_of_analysis_summaries[
        UnitOfAnalysis.COMMODITY_SOURCE
    ]
    assert _texts(commodities.regions) == {"Brazil"}
    assert _texts(commodities.commodities) == {"Arabica"}


def test_versioned_summary_excludes_tombstoned_entities(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    versioned_org_uid: uuid.UUID,
):
    parent = _change_set(test_admin_session, versioned_org_uid)
    alive = _commodity(
        test_admin_session,
        versioned_org_uid,
        parent.uid,
        "Alive",
        commodity_type="Arabica",
        country="Brazil",
        admin_1=None,
        supplier="Supplier A",
        product="Product A",
    )
    dead = _commodity(
        test_admin_session,
        versioned_org_uid,
        parent.uid,
        "Dead",
        commodity_type="Robusta",
        country="Vietnam",
        admin_1=None,
        supplier="Supplier B",
        product="Product B",
    )
    assert alive.uid != dead.uid

    child = _change_set(
        test_admin_session, versioned_org_uid, parent_uid=parent.uid
    )
    _record(
        test_admin_session,
        versioned_org_uid,
        child.uid,
        CommodityLocationEntity.__tablename__,
        previous_uid=dead.uid,
    )

    summary = get_change_summary(
        test_admin_session,
        org_uid=versioned_org_uid,
        change_set_uid=child.uid,
    )

    commodities = summary.unit_of_analysis_summaries[
        UnitOfAnalysis.COMMODITY_SOURCE
    ]
    assert _texts(commodities.regions) == {"Brazil"}


def test_versioned_summary_labels_missing_values_unknown(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    versioned_org_uid: uuid.UUID,
):
    cs = _change_set(test_admin_session, versioned_org_uid)
    _commodity(
        test_admin_session,
        versioned_org_uid,
        cs.uid,
        "COMMOD 1",
        commodity_type="Arabica",
        country=None,
        admin_1=None,
        supplier=None,
        product=None,
    )

    summary = get_change_summary(
        test_admin_session,
        org_uid=versioned_org_uid,
        change_set_uid=cs.uid,
    )

    commodities = summary.unit_of_analysis_summaries[
        UnitOfAnalysis.COMMODITY_SOURCE
    ]
    assert _texts(commodities.regions) == {"unknown"}
    assert _texts(commodities.suppliers) == {"unknown"}
    assert _texts(commodities.products) == {"unknown"}


def test_versioned_summary_is_empty_for_empty_change_set(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    versioned_org_uid: uuid.UUID,
):
    cs = _change_set(test_admin_session, versioned_org_uid)

    summary = get_change_summary(
        test_admin_session,
        org_uid=versioned_org_uid,
        change_set_uid=cs.uid,
    )

    assert summary.unit_of_analysis_summaries == {}


def test_versioned_summary_isolates_other_orgs(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    versioned_org_uid: uuid.UUID,
    other_org_uid: uuid.UUID,
):
    cs = _change_set(test_admin_session, versioned_org_uid)
    _commodity(
        test_admin_session,
        versioned_org_uid,
        cs.uid,
        "Own",
        commodity_type="Arabica",
        country="Brazil",
        admin_1=None,
        supplier="Supplier A",
        product="Product A",
    )

    other_cs = _change_set(test_admin_session, other_org_uid)
    _commodity(
        test_admin_session,
        other_org_uid,
        other_cs.uid,
        "Other",
        commodity_type="Robusta",
        country="Vietnam",
        admin_1=None,
        supplier="Supplier B",
        product="Product B",
    )

    summary = get_change_summary(
        test_admin_session,
        org_uid=versioned_org_uid,
        change_set_uid=cs.uid,
    )

    commodities = summary.unit_of_analysis_summaries[
        UnitOfAnalysis.COMMODITY_SOURCE
    ]
    assert _texts(commodities.regions) == {"Brazil"}
