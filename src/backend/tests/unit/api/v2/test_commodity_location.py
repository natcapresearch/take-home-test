"""Unit tests for src/backend/app/api/v2/commodity_location.py."""

import uuid
from collections.abc import Callable

import pytest
from src.backend.app.access import SafeSession
from src.backend.app.api.v2.commodity_location import (
    get_aggregated_commodity_regions,
    get_commodity_sources,
    get_commodity_summary,
)
from src.backend.app.config import settings
from src.backend.app.models.admin_region import AdminRegion
from src.backend.app.models.change_set import Change, ChangeSet
from src.backend.app.models.commodity_location_entity import (
    CommodityLocationEntity,
)
from src.backend.app.models.export.exported_commodity_location import (
    ExportedCommodityLocation,
)
from src.backend.app.models.organisation import Organisation
from src.backend.app.util.enums import (
    AdminRegionLevel,
    ChangeSetState,
    EntityScope,
    SortOrder,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_org(session: SafeSession, *, name: str = "Test Org") -> Organisation:
    org = Organisation(
        name=name,
        authorised_email_domains=["test.com"],
    )
    session.add(org)
    session.flush()
    return org


def _make_changeset(
    session: SafeSession,
    org_uid: uuid.UUID,
    *,
    parent_uid: uuid.UUID | None = None,
) -> ChangeSet:
    cs = ChangeSet(
        org_uid=org_uid,
        state=ChangeSetState.DONE,
        parent_uid=parent_uid,
    )
    session.add(cs)
    session.flush()
    return cs


def _register_tombstone(
    session: SafeSession,
    org_uid: uuid.UUID,
    change_set_uid: uuid.UUID,
    entity: CommodityLocationEntity,
) -> None:
    change = Change(
        org_uid=org_uid,
        change_set_uid=change_set_uid,
        model_type=CommodityLocationEntity.__tablename__,
        new_uid=None,
        previous_uid=entity.uid,
        description=f"Deleted {entity.uid}",
    )
    session.add(change)
    session.flush()


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def org_uid(
    set_up_test_db: None,
    test_admin_session: SafeSession,
) -> uuid.UUID:
    org = _make_org(test_admin_session)
    return org.uid


# ---------------------------------------------------------------------------
# get_commodity_summary — empty changeset
# ---------------------------------------------------------------------------


def test_get_commodity_summary_empty_changeset_returns_zeros(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    result = get_commodity_summary(test_admin_session, org_uid, cs.uid)

    assert result.total_commodities == 0
    assert result.total_suppliers == 0
    assert result.total_locations == 0
    assert result.total_spend is None
    assert result.total_quantity is None
    # bool_and on empty set returns NULL → None
    assert result.all_commodities_have_quantity is None
    assert result.all_commodities_have_spend is None
    assert result.missing_quantity_count == 0
    assert result.missing_spend_count == 0
    assert result.total_commodity_sources == 0


# ---------------------------------------------------------------------------
# get_commodity_summary — single commodity with all fields
# ---------------------------------------------------------------------------


def test_get_commodity_summary_single_commodity_full_data(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    entity = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="C001",
        commodity_subgroup="Almonds",
        supplier="Nut Corp",
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, entity)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity.uid,
        commodity_subgroup="Almonds",
        sourcing_country_name="USA",
        quantity_kilograms=800.0,
        spend=400.0,
        change_set_uid=cs.uid,
    )

    result = get_commodity_summary(test_admin_session, org_uid, cs.uid)

    assert result.total_commodities == 1
    assert result.total_suppliers == 1
    assert result.total_locations == 1
    assert result.total_spend == 400
    assert result.total_quantity == pytest.approx(800.0)
    assert result.all_commodities_have_quantity is True
    assert result.all_commodities_have_spend is True
    assert result.commodity_subgroups == ["Almonds"]
    assert result.sourcing_countries == ["USA"]
    assert result.supplier_names == ["Nut Corp"]


# ---------------------------------------------------------------------------
# get_commodity_summary — distinct aggregation across multiple commodities
# ---------------------------------------------------------------------------


def test_get_commodity_summary_counts_distinct_subgroups_suppliers_locations(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    # Three entities, sharing subgroup and country but different supplier
    specs = [
        ("C001", "Cereals", "France", "Supplier A"),
        ("C002", "Cereals", "France", "Supplier B"),
        ("C003", "Nuts", "Germany", "Supplier A"),
    ]
    for identifier, subgroup, country, supplier in specs:
        entity = make_commodity_location_entity(
            test_admin_session,
            org_uid,
            identifier=identifier,
            commodity_subgroup=subgroup,
            normalised_key=identifier.lower(),
            supplier=supplier,
        )
        make_creation_change(test_admin_session, org_uid, cs.uid, entity)
        make_exported_commodity_location(
            test_admin_session,
            org_uid,
            entity.uid,
            commodity_subgroup=subgroup,
            identifier=identifier,
            sourcing_country_name=country,
            quantity_kilograms=100.0,
            spend=50.0,
            change_set_uid=cs.uid,
        )

    result = get_commodity_summary(test_admin_session, org_uid, cs.uid)

    # 2 distinct subgroups (Cereals, Nuts)
    assert result.total_commodities == 2
    # 2 distinct suppliers (Supplier A, Supplier B)
    assert result.total_suppliers == 2
    # 2 distinct countries (France, Germany)
    assert result.total_locations == 2
    assert result.total_spend == 150
    assert result.total_quantity == pytest.approx(300.0)
    assert result.commodity_subgroups == ["Cereals", "Nuts"]
    assert result.sourcing_countries == ["France", "Germany"]
    assert result.supplier_names == ["Supplier A", "Supplier B"]


# ---------------------------------------------------------------------------
# get_commodity_summary — null spend/quantity: coalesced to 0, bool_and False
# ---------------------------------------------------------------------------


def test_get_commodity_summary_null_spend_and_quantity(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    entity_a = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C001", normalised_key="c001"
    )
    entity_b = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C002", normalised_key="c002"
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, entity_a)
    make_creation_change(test_admin_session, org_uid, cs.uid, entity_b)

    # entity_a: both null
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity_a.uid,
        identifier="C001",
        quantity_kilograms=None,
        spend=None,
        change_set_uid=cs.uid,
    )
    # entity_b: both present
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity_b.uid,
        identifier="C002",
        quantity_kilograms=200.0,
        spend=100.0,
        change_set_uid=cs.uid,
    )

    result = get_commodity_summary(test_admin_session, org_uid, cs.uid)

    # Coalesce: 0 + 200 = 200, 0 + 100 = 100
    assert result.total_quantity == pytest.approx(200.0)
    assert result.total_spend == 100
    # Not all commodities have quantity/spend
    assert result.all_commodities_have_quantity is False
    assert result.all_commodities_have_spend is False


# ---------------------------------------------------------------------------
# get_commodity_summary — missing information counts and categorisation
# ---------------------------------------------------------------------------


def test_get_commodity_summary_missing_information_categorizes_reasons(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    """Quantity, spend gaps are each counted individually."""
    cs = _make_changeset(test_admin_session, org_uid)

    entity_complete = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C001", normalised_key="c001"
    )
    entity_missing_qty = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C002", normalised_key="c002"
    )
    entity_missing_spend = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C003", normalised_key="c003"
    )
    for entity in (
        entity_complete,
        entity_missing_qty,
        entity_missing_spend,
    ):
        make_creation_change(test_admin_session, org_uid, cs.uid, entity)

    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity_complete.uid,
        identifier="C001",
        sourcing_administrative_level_1_name="Normandy",
        change_set_uid=cs.uid,
    )
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity_missing_qty.uid,
        identifier="C002",
        sourcing_administrative_level_1_name="Normandy",
        quantity_kilograms=None,
        change_set_uid=cs.uid,
    )
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity_missing_spend.uid,
        identifier="C003",
        sourcing_administrative_level_1_name="Normandy",
        spend=None,
        change_set_uid=cs.uid,
    )

    result = get_commodity_summary(test_admin_session, org_uid, cs.uid)

    assert result.missing_quantity_count == 1
    assert result.missing_spend_count == 1
    # 3 resolved rows total: 1-of-3 missing is "partial", distinguishable
    # from "none have this field" (missing_*_count == total_commodity_sources).
    assert result.total_commodity_sources == 3


def test_get_commodity_summary_none_have_spend(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    """When every resolved row is missing a field, missing_*_count equals
    total_commodity_sources - the "none at all" case."""
    cs = _make_changeset(test_admin_session, org_uid)

    entity_a = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C001", normalised_key="c001"
    )
    entity_b = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C002", normalised_key="c002"
    )
    for entity in (entity_a, entity_b):
        make_creation_change(test_admin_session, org_uid, cs.uid, entity)

    for entity, identifier in ((entity_a, "C001"), (entity_b, "C002")):
        make_exported_commodity_location(
            test_admin_session,
            org_uid,
            entity.uid,
            identifier=identifier,
            sourcing_administrative_level_1_name="Normandy",
            spend=None,
            change_set_uid=cs.uid,
        )

    result = get_commodity_summary(test_admin_session, org_uid, cs.uid)

    assert result.missing_spend_count == 2
    assert result.total_commodity_sources == 2
    assert result.missing_spend_count == result.total_commodity_sources


# ---------------------------------------------------------------------------
# get_commodity_summary — entity without export: bool_and False (null from join)
# ---------------------------------------------------------------------------


def test_get_commodity_summary_entity_without_export_makes_bool_and_false(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    entity_with = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C001", normalised_key="c001"
    )
    entity_without = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C002", normalised_key="c002"
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, entity_with)
    make_creation_change(test_admin_session, org_uid, cs.uid, entity_without)

    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity_with.uid,
        identifier="C001",
        quantity_kilograms=100.0,
        spend=50.0,
        change_set_uid=cs.uid,
    )
    # entity_without has no ExportedCommodityLocation → outer join yields NULL

    result = get_commodity_summary(test_admin_session, org_uid, cs.uid)

    assert result.total_commodities == 1  # entity_without has no subgroup data
    # NULL IS NOT NULL = FALSE → bool_and includes a FALSE
    assert result.all_commodities_have_quantity is False
    assert result.all_commodities_have_spend is False


# ---------------------------------------------------------------------------
# get_commodity_summary — tombstoned entities excluded
# ---------------------------------------------------------------------------


def test_get_commodity_summary_excludes_tombstoned(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    parent = _make_changeset(test_admin_session, org_uid)

    alive = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="alive",
        normalised_key="alive",
        supplier="Supplier A",
    )
    dead = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="dead",
        normalised_key="dead",
        supplier="Supplier B",
    )
    make_creation_change(test_admin_session, org_uid, parent.uid, alive)
    make_creation_change(test_admin_session, org_uid, parent.uid, dead)

    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        alive.uid,
        identifier="alive",
        commodity_subgroup="Cereals",
        sourcing_country_name="France",
        quantity_kilograms=100.0,
        spend=50.0,
        change_set_uid=parent.uid,
    )
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        dead.uid,
        identifier="dead",
        commodity_subgroup="Nuts",
        sourcing_country_name="Germany",
        quantity_kilograms=200.0,
        spend=100.0,
        change_set_uid=parent.uid,
    )

    child = _make_changeset(test_admin_session, org_uid, parent_uid=parent.uid)
    _register_tombstone(test_admin_session, org_uid, child.uid, dead)

    result = get_commodity_summary(test_admin_session, org_uid, child.uid)

    assert result.total_commodities == 1
    assert result.total_suppliers == 1
    assert result.total_locations == 1
    assert result.total_spend == 50
    assert result.total_quantity == pytest.approx(100.0)


def test_get_commodity_summary_scope_all_keeps_entities_outside_changeset(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    """Under scope=all a tombstoned entity still contributes its values.

    The group member list shows entities outside the browsed version, so the
    filter dropdowns beside it have to offer the values those rows carry —
    resolved from each entity's most recent export row when the changeset
    holds none.
    """
    parent = _make_changeset(test_admin_session, org_uid)

    dead = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="dead",
        normalised_key="dead",
        supplier="Supplier B",
    )
    make_creation_change(test_admin_session, org_uid, parent.uid, dead)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        dead.uid,
        identifier="dead",
        commodity_subgroup="Nuts",
        sourcing_country_name="Germany",
        quantity_kilograms=200.0,
        spend=100.0,
        change_set_uid=parent.uid,
    )

    child = _make_changeset(test_admin_session, org_uid, parent_uid=parent.uid)
    _register_tombstone(test_admin_session, org_uid, child.uid, dead)

    alive_only = get_commodity_summary(test_admin_session, org_uid, child.uid)
    assert alive_only.commodity_subgroups == []
    assert alive_only.sourcing_countries == []
    assert alive_only.supplier_names == []

    everything = get_commodity_summary(
        test_admin_session, org_uid, child.uid, scope=EntityScope.ALL
    )
    assert everything.commodity_subgroups == ["Nuts"]
    assert everything.sourcing_countries == ["Germany"]
    assert everything.supplier_names == ["Supplier B"]


def test_get_commodity_summary_scope_all_with_every_value_null(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    """scope=all over rows whose spend and quantity are NULL must not error.

    Under scope=all the resolved export rows are materialised into a literal
    VALUES clause, and SQLAlchemy renders a None as a bare untyped NULL. With
    no non-NULL row to infer a type from, Postgres defaults the column to text
    and sum() fails with "function sum(text) does not exist" unless the
    aggregate casts explicitly. A group whose sources all lack a quantity hits
    this on the first click with no filters applied, so it is not an edge case.

    The sibling tests miss it from both sides: the null-value test runs under
    the default ALIVE scope, where the rows come from a real subquery whose
    columns are already typed, and the other scope=all test supplies non-NULL
    values, which let Postgres infer double precision.
    """
    cs = _make_changeset(test_admin_session, org_uid)

    entity = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C001", normalised_key="c001"
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, entity)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity.uid,
        identifier="C001",
        quantity_kilograms=None,
        spend=None,
        change_set_uid=cs.uid,
    )

    result = get_commodity_summary(
        test_admin_session, org_uid, cs.uid, scope=EntityScope.ALL
    )

    assert result.total_quantity is None
    assert result.total_spend is None
    assert result.all_commodities_have_quantity is False
    assert result.all_commodities_have_spend is False


def test_get_commodity_summary_explicit_zero_is_not_missing(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    """A spend / quantity uploaded as 0 sums to 0, not to the missing NULL."""
    cs = _make_changeset(test_admin_session, org_uid)

    entity = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C001", normalised_key="c001"
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, entity)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity.uid,
        identifier="C001",
        quantity_kilograms=0.0,
        spend=0,
        change_set_uid=cs.uid,
    )

    result = get_commodity_summary(test_admin_session, org_uid, cs.uid)

    assert result.total_quantity == 0
    assert result.total_spend == 0
    assert result.all_commodities_have_quantity is True
    assert result.all_commodities_have_spend is True


# ---------------------------------------------------------------------------
# get_commodity_summary — parent chain inheritance
# ---------------------------------------------------------------------------


def test_get_commodity_summary_inherits_from_parent_chain(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs1 = _make_changeset(test_admin_session, org_uid)
    entity1 = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="P001",
        normalised_key="p001",
        supplier="S1",
    )
    make_creation_change(test_admin_session, org_uid, cs1.uid, entity1)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity1.uid,
        identifier="P001",
        commodity_subgroup="Cereals",
        sourcing_country_name="France",
        quantity_kilograms=100.0,
        spend=50.0,
        change_set_uid=cs1.uid,
    )

    cs2 = _make_changeset(test_admin_session, org_uid, parent_uid=cs1.uid)
    entity2 = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="C001",
        normalised_key="c001",
        supplier="S2",
    )
    make_creation_change(test_admin_session, org_uid, cs2.uid, entity2)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity2.uid,
        identifier="C001",
        commodity_subgroup="Nuts",
        sourcing_country_name="Germany",
        quantity_kilograms=200.0,
        spend=100.0,
        change_set_uid=cs2.uid,
    )

    result = get_commodity_summary(test_admin_session, org_uid, cs2.uid)

    assert result.total_commodities == 2
    assert result.total_suppliers == 2
    assert result.total_locations == 2
    assert result.total_spend == 150
    assert result.total_quantity == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# get_commodity_summary — org isolation
# ---------------------------------------------------------------------------


def test_get_commodity_summary_does_not_include_other_org_commodities(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    other_org = _make_org(test_admin_session, name="Other Org")

    cs_own = _make_changeset(test_admin_session, org_uid)
    own = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="OWN"
    )
    make_creation_change(test_admin_session, org_uid, cs_own.uid, own)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        own.uid,
        identifier="OWN",
        commodity_subgroup="Cereals",
        quantity_kilograms=100.0,
        spend=50.0,
        change_set_uid=cs_own.uid,
    )

    cs_other = _make_changeset(test_admin_session, other_org.uid)
    other = make_commodity_location_entity(
        test_admin_session, other_org.uid, identifier="OTHER"
    )
    make_creation_change(test_admin_session, other_org.uid, cs_other.uid, other)
    make_exported_commodity_location(
        test_admin_session,
        other_org.uid,
        other.uid,
        identifier="OTHER",
        commodity_subgroup="Nuts",
        quantity_kilograms=999.0,
        spend=999.0,
        change_set_uid=cs_other.uid,
    )

    result = get_commodity_summary(test_admin_session, org_uid, cs_own.uid)

    assert result.total_commodities == 1
    assert result.total_spend == 50


# ---------------------------------------------------------------------------
# get_commodity_summary — resolves the snapshot for the requested change set,
# not whichever one is newest by created_at
# ---------------------------------------------------------------------------


def test_get_commodity_summary_picks_snapshot_from_requested_change_set(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    parent = _make_changeset(test_admin_session, org_uid)

    entity = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C001"
    )
    make_creation_change(test_admin_session, org_uid, parent.uid, entity)

    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity.uid,
        identifier="C001",
        commodity_subgroup="Cereals",
        sourcing_country_name="OldCountry",
        quantity_kilograms=9999.0,
        spend=9999.0,
        change_set_uid=parent.uid,
    )
    # A later, child change set gets its own (newer) snapshot for the same
    # entity — this must not leak into the parent's view.
    child = _make_changeset(test_admin_session, org_uid, parent_uid=parent.uid)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity.uid,
        identifier="C001",
        commodity_subgroup="Cereals",
        sourcing_country_name="NewCountry",
        quantity_kilograms=100.0,
        spend=50.0,
        change_set_uid=child.uid,
    )

    parent_result = get_commodity_summary(
        test_admin_session, org_uid, parent.uid
    )
    child_result = get_commodity_summary(test_admin_session, org_uid, child.uid)

    assert parent_result.total_spend == 9999
    assert parent_result.total_quantity == pytest.approx(9999.0)
    assert child_result.total_spend == 50
    assert child_result.total_quantity == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# get_commodity_sources — correct field mapping
# ---------------------------------------------------------------------------


def test_get_commodity_sources_returns_correct_fields(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    entity = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="FIELD-001",
        commodity_type="Crop",
        commodity_subgroup="Barley",
        commodity_code="BARLEY",
        year_purchased=2023,
        supplier="Barley Corp",
        product="Barley Premium",
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, entity)
    # Export snapshot carries a different supplier/product to prove they are
    # ignored: supplier/product must come from the immutable entity, since a
    # product/supplier change always mints a new CommodityLocationEntity
    # (see normalised_key) rather than mutating this one.
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity.uid,
        identifier="FIELD-001",
        commodity_type="Crop",
        commodity_subgroup="Barley",
        commodity_code="BARLEY",
        year_purchased=2023,
        sourcing_country_name="Germany",
        sourcing_administrative_level_1_name="Bavaria",
        supplier="Wrong Supplier",
        product="Wrong Product",
        quantity_kilograms=500.0,
        spend=250.0,
        change_set_uid=cs.uid,
    )

    results, _ = get_commodity_sources(test_admin_session, org_uid, cs.uid)

    assert len(results) == 1
    src = results[0]
    assert src.entity_uid == entity.uid
    assert src.org_uid == org_uid
    assert src.identifier == "FIELD-001"
    assert src.commodity_type == "Crop"
    assert src.commodity_subgroup == "Barley"
    assert src.commodity_code == "BARLEY"
    assert src.year_purchased == 2023
    assert src.sourcing_country == "Germany"
    assert src.sourcing_region == "Bavaria"
    assert src.supplier == "Barley Corp"
    assert src.product == "Barley Premium"
    assert src.quantity_kilograms == pytest.approx(500.0)
    assert src.spend == pytest.approx(250.0)


# ---------------------------------------------------------------------------
# get_commodity_sources — null optional fields pass through as None
# ---------------------------------------------------------------------------


def test_get_commodity_sources_null_optional_fields(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    entity = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C001"
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, entity)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity.uid,
        identifier="C001",
        sourcing_country_name=None,
        sourcing_administrative_level_1_name=None,
        supplier=None,
        product=None,
        quantity_kilograms=None,
        spend=None,
        change_set_uid=cs.uid,
    )

    results, _ = get_commodity_sources(test_admin_session, org_uid, cs.uid)

    assert len(results) == 1
    src = results[0]
    assert src.sourcing_country is None
    assert src.sourcing_region is None
    assert src.supplier is None
    assert src.product is None
    assert src.quantity_kilograms is None
    assert src.spend is None


# ---------------------------------------------------------------------------
# get_commodity_sources — entity without export returns entity fields, None exports
# ---------------------------------------------------------------------------


def test_get_commodity_sources_entity_without_export(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    entity = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="BARE-001",
        commodity_type="Livestock",
        commodity_subgroup="Cattle",
        commodity_code="CATTLE",
        year_purchased=2022,
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, entity)

    results, _ = get_commodity_sources(test_admin_session, org_uid, cs.uid)

    assert len(results) == 1
    src = results[0]
    assert src.entity_uid == entity.uid
    assert src.identifier == "BARE-001"
    assert src.commodity_type == "Livestock"
    assert src.commodity_subgroup == "Cattle"
    assert src.commodity_code == "CATTLE"
    assert src.year_purchased == 2022
    # Export fields all None from outer join
    assert src.sourcing_country is None
    assert src.sourcing_region is None
    assert src.quantity_kilograms is None
    assert src.spend is None
    assert src.supplier is None
    assert src.product is None


# ---------------------------------------------------------------------------
# get_commodity_sources — limit parameter is enforced
# ---------------------------------------------------------------------------


def test_get_commodity_sources_limit_restricts_result_count(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    for i in range(5):
        entity = make_commodity_location_entity(
            test_admin_session,
            org_uid,
            identifier=f"C{i:03d}",
            normalised_key=f"c{i:03d}",
        )
        make_creation_change(test_admin_session, org_uid, cs.uid, entity)
        make_exported_commodity_location(
            test_admin_session,
            org_uid,
            entity.uid,
            identifier=f"C{i:03d}",
            change_set_uid=cs.uid,
        )

    results, _ = get_commodity_sources(
        test_admin_session, org_uid, cs.uid, limit=3
    )

    assert len(results) == 3


def test_get_commodity_sources_default_limit_matches_default_page_size(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    """Regression test: /commodity-sources/ used to default to limit=10000
    (effectively unpaginated). It should default to
    settings.DEFAULT_PAGE_SIZE like every other paginated list endpoint
    unless a caller explicitly asks for more."""
    cs = _make_changeset(test_admin_session, org_uid)

    total = settings.DEFAULT_PAGE_SIZE + 1
    for i in range(total):
        entity = make_commodity_location_entity(
            test_admin_session,
            org_uid,
            identifier=f"C{i:03d}",
            normalised_key=f"c{i:03d}",
        )
        make_creation_change(test_admin_session, org_uid, cs.uid, entity)
        make_exported_commodity_location(
            test_admin_session,
            org_uid,
            entity.uid,
            identifier=f"C{i:03d}",
            change_set_uid=cs.uid,
        )

    results, paginator = get_commodity_sources(
        test_admin_session, org_uid, cs.uid
    )

    assert len(results) == settings.DEFAULT_PAGE_SIZE
    assert paginator.total_count == total
    assert paginator.next_cursor is not None


# ---------------------------------------------------------------------------
# get_commodity_sources — org isolation
# ---------------------------------------------------------------------------


def test_get_commodity_sources_excludes_other_org_entities(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    other_org = _make_org(test_admin_session, name="Other Org")

    cs_own = _make_changeset(test_admin_session, org_uid)
    own = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="OWN"
    )
    make_creation_change(test_admin_session, org_uid, cs_own.uid, own)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        own.uid,
        identifier="OWN",
        change_set_uid=cs_own.uid,
    )

    cs_other = _make_changeset(test_admin_session, other_org.uid)
    other = make_commodity_location_entity(
        test_admin_session, other_org.uid, identifier="OTHER"
    )
    make_creation_change(test_admin_session, other_org.uid, cs_other.uid, other)
    make_exported_commodity_location(
        test_admin_session,
        other_org.uid,
        other.uid,
        identifier="OTHER",
        change_set_uid=cs_other.uid,
    )

    results, _ = get_commodity_sources(test_admin_session, org_uid, cs_own.uid)

    assert len(results) == 1
    assert results[0].entity_uid == own.uid


# ---------------------------------------------------------------------------
# get_commodity_sources — resolves the snapshot for the requested change set,
# not whichever one is newest by created_at
# ---------------------------------------------------------------------------


def test_get_commodity_sources_picks_snapshot_from_requested_change_set(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    parent = _make_changeset(test_admin_session, org_uid)

    entity = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="VERSIONED"
    )
    make_creation_change(test_admin_session, org_uid, parent.uid, entity)

    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity.uid,
        identifier="VERSIONED",
        sourcing_country_name="OldCountry",
        quantity_kilograms=9999.0,
        spend=9999.0,
        change_set_uid=parent.uid,
    )
    # A later, child change set gets its own (newer) snapshot for the same
    # entity — this must not leak into the parent's view.
    child = _make_changeset(test_admin_session, org_uid, parent_uid=parent.uid)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        entity.uid,
        identifier="VERSIONED",
        sourcing_country_name="NewCountry",
        quantity_kilograms=100.0,
        spend=50.0,
        change_set_uid=child.uid,
    )

    parent_results, _ = get_commodity_sources(
        test_admin_session, org_uid, parent.uid
    )
    child_results, _ = get_commodity_sources(
        test_admin_session, org_uid, child.uid
    )

    assert parent_results[0].sourcing_country == "OldCountry"
    assert parent_results[0].quantity_kilograms == pytest.approx(9999.0)
    assert parent_results[0].spend == pytest.approx(9999.0)

    assert child_results[0].sourcing_country == "NewCountry"
    assert child_results[0].quantity_kilograms == pytest.approx(100.0)
    assert child_results[0].spend == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# get_commodity_sources — tombstoned entity not returned
# ---------------------------------------------------------------------------


def test_get_commodity_sources_excludes_tombstoned_entity(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    parent = _make_changeset(test_admin_session, org_uid)

    alive = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="ALIVE", normalised_key="alive"
    )
    dead = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="DEAD", normalised_key="dead"
    )
    make_creation_change(test_admin_session, org_uid, parent.uid, alive)
    make_creation_change(test_admin_session, org_uid, parent.uid, dead)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        alive.uid,
        identifier="ALIVE",
        change_set_uid=parent.uid,
    )
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        dead.uid,
        identifier="DEAD",
        change_set_uid=parent.uid,
    )

    child = _make_changeset(test_admin_session, org_uid, parent_uid=parent.uid)
    _register_tombstone(test_admin_session, org_uid, child.uid, dead)

    results, _ = get_commodity_sources(test_admin_session, org_uid, child.uid)

    assert len(results) == 1
    assert results[0].entity_uid == alive.uid


# ---------------------------------------------------------------------------
# get_commodity_sources — filtering
# ---------------------------------------------------------------------------


def test_get_commodity_sources_filters_by_commodity_subgroup_substring(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    match = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="MATCH",
        commodity_subgroup="Cereals",
        normalised_key="match",
    )
    other = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="OTHER",
        commodity_subgroup="Livestock",
        normalised_key="other",
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, match)
    make_creation_change(test_admin_session, org_uid, cs.uid, other)

    results, _ = get_commodity_sources(
        test_admin_session, org_uid, cs.uid, commodity_subgroup="cereal"
    )

    assert len(results) == 1
    assert results[0].entity_uid == match.uid


def test_get_commodity_sources_filters_by_commodity_subgroups_exact(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
) -> None:
    """The typeahead pickers send exact subgroup names, one per pick.

    Regression test: this endpoint accepted only the singular substring
    filter, so the group picker's commodity search was dropped and the
    whole org came back unfiltered.
    """
    cs = _make_changeset(test_admin_session, org_uid)

    maize = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="MAIZE",
        commodity_subgroup="Maize (corn)",
        normalised_key="maize",
    )
    apples = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="APPLES",
        commodity_subgroup="Apples",
        normalised_key="apples",
    )
    other = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="OTHER",
        commodity_subgroup="Livestock",
        normalised_key="other",
    )
    for entity in (maize, apples, other):
        make_creation_change(test_admin_session, org_uid, cs.uid, entity)

    results, _ = get_commodity_sources(
        test_admin_session,
        org_uid,
        cs.uid,
        commodity_subgroups=["Maize (corn)", "Apples"],
    )

    assert {result.entity_uid for result in results} == {maize.uid, apples.uid}


def test_get_commodity_sources_commodity_subgroups_does_not_match_substrings(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
) -> None:
    """commodity_subgroups is the exact filter; commodity_subgroup is the
    substring one."""
    cs = _make_changeset(test_admin_session, org_uid)

    entity = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="MAIZE",
        commodity_subgroup="Maize (corn)",
        normalised_key="maize",
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, entity)

    results, _ = get_commodity_sources(
        test_admin_session, org_uid, cs.uid, commodity_subgroups=["Maize"]
    )

    assert results == []


def test_get_commodity_sources_filters_by_suppliers(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    acme = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="ACME",
        normalised_key="acme",
        supplier="Acme Corp",
    )
    other = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="OTHERSUP",
        normalised_key="othersup",
        supplier="Other Corp",
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, acme)
    make_creation_change(test_admin_session, org_uid, cs.uid, other)

    results, _ = get_commodity_sources(
        test_admin_session, org_uid, cs.uid, suppliers=["Acme Corp"]
    )

    assert len(results) == 1
    assert results[0].entity_uid == acme.uid


def test_get_commodity_sources_filters_by_product_names(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    widget = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="WIDGET",
        normalised_key="widget",
        product="Widget",
    )
    gadget = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="GADGET",
        normalised_key="gadget",
        product="Gadget",
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, widget)
    make_creation_change(test_admin_session, org_uid, cs.uid, gadget)

    results, _ = get_commodity_sources(
        test_admin_session, org_uid, cs.uid, product_names=["Widget"]
    )

    assert len(results) == 1
    assert results[0].entity_uid == widget.uid


def test_get_commodity_sources_filters_by_countries(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    japan = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="JAPAN", normalised_key="japan"
    )
    france = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="FRANCE",
        normalised_key="france",
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, japan)
    make_creation_change(test_admin_session, org_uid, cs.uid, france)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        japan.uid,
        identifier="JAPAN",
        sourcing_country_name="Japan",
        change_set_uid=cs.uid,
    )
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        france.uid,
        identifier="FRANCE",
        sourcing_country_name="France",
        change_set_uid=cs.uid,
    )

    results, _ = get_commodity_sources(
        test_admin_session, org_uid, cs.uid, countries=["Japan"]
    )

    assert len(results) == 1
    assert results[0].entity_uid == japan.uid


def test_get_commodity_sources_filters_by_sourcing_administrative_level_1_names(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    bavaria = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="BAVARIA",
        normalised_key="bavaria",
    )
    saxony = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="SAXONY",
        normalised_key="saxony",
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, bavaria)
    make_creation_change(test_admin_session, org_uid, cs.uid, saxony)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        bavaria.uid,
        identifier="BAVARIA",
        sourcing_administrative_level_1_name="Bavaria",
        change_set_uid=cs.uid,
    )
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        saxony.uid,
        identifier="SAXONY",
        sourcing_administrative_level_1_name="Saxony",
        change_set_uid=cs.uid,
    )

    results, _ = get_commodity_sources(
        test_admin_session,
        org_uid,
        cs.uid,
        sourcing_administrative_level_1_names=["Bavaria"],
    )

    assert len(results) == 1
    assert results[0].entity_uid == bavaria.uid


# ---------------------------------------------------------------------------
# get_commodity_sources — sorting by export-only columns (extra sort columns)
# ---------------------------------------------------------------------------


def test_get_commodity_sources_sort_by_sourcing_country(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    zebra = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="ZEBRA", normalised_key="zebra"
    )
    alpha = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="ALPHA", normalised_key="alpha"
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, zebra)
    make_creation_change(test_admin_session, org_uid, cs.uid, alpha)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        zebra.uid,
        identifier="ZEBRA",
        sourcing_country_name="Zebra Country",
        change_set_uid=cs.uid,
    )
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        alpha.uid,
        identifier="ALPHA",
        sourcing_country_name="Alpha Country",
        change_set_uid=cs.uid,
    )

    results, _ = get_commodity_sources(
        test_admin_session,
        org_uid,
        cs.uid,
        sort_on="sourcing_country",
        sort_order=SortOrder.ASC,
    )

    assert [r.entity_uid for r in results] == [alpha.uid, zebra.uid]


def test_get_commodity_sources_sort_by_sourcing_region(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    zebra = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="ZEBRA", normalised_key="zebra"
    )
    alpha = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="ALPHA", normalised_key="alpha"
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, zebra)
    make_creation_change(test_admin_session, org_uid, cs.uid, alpha)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        zebra.uid,
        identifier="ZEBRA",
        sourcing_administrative_level_1_name="Zebra Region",
        change_set_uid=cs.uid,
    )
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        alpha.uid,
        identifier="ALPHA",
        sourcing_administrative_level_1_name="Alpha Region",
        change_set_uid=cs.uid,
    )

    results, _ = get_commodity_sources(
        test_admin_session,
        org_uid,
        cs.uid,
        sort_on="sourcing_region",
        sort_order=SortOrder.ASC,
    )

    assert [r.entity_uid for r in results] == [alpha.uid, zebra.uid]


def test_get_commodity_sources_sort_by_spend(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    low = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="LOW", normalised_key="low"
    )
    high = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="HIGH", normalised_key="high"
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, low)
    make_creation_change(test_admin_session, org_uid, cs.uid, high)
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        low.uid,
        identifier="LOW",
        spend=10.0,
        change_set_uid=cs.uid,
    )
    make_exported_commodity_location(
        test_admin_session,
        org_uid,
        high.uid,
        identifier="HIGH",
        spend=1000.0,
        change_set_uid=cs.uid,
    )

    results, _ = get_commodity_sources(
        test_admin_session,
        org_uid,
        cs.uid,
        sort_on="spend",
        sort_order=SortOrder.ASC,
    )

    assert [r.entity_uid for r in results] == [low.uid, high.uid]


def test_get_commodity_sources_sort_by_supplier(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    first = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="C-A",
        normalised_key="c-a",
        supplier="AAA Supplier",
    )
    second = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="C-B",
        normalised_key="c-b",
        supplier="ZZZ Supplier",
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, first)
    make_creation_change(test_admin_session, org_uid, cs.uid, second)

    results, _ = get_commodity_sources(
        test_admin_session,
        org_uid,
        cs.uid,
        sort_on="supplier",
        sort_order=SortOrder.ASC,
    )

    assert [r.supplier for r in results] == ["AAA Supplier", "ZZZ Supplier"]


def test_get_commodity_sources_sort_by_product(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)

    first = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="C-A",
        normalised_key="c-a",
        product="AAA Product",
    )
    second = make_commodity_location_entity(
        test_admin_session,
        org_uid,
        identifier="C-B",
        normalised_key="c-b",
        product="ZZZ Product",
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, first)
    make_creation_change(test_admin_session, org_uid, cs.uid, second)

    results, _ = get_commodity_sources(
        test_admin_session,
        org_uid,
        cs.uid,
        sort_on="product",
        sort_order=SortOrder.ASC,
    )

    assert [r.product for r in results] == ["AAA Product", "ZZZ Product"]


@pytest.mark.parametrize("sort_order", [SortOrder.ASC, SortOrder.DESC])
def test_get_commodity_sources_breaks_ties_on_identifier_not_uid(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    sort_order: SortOrder,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
) -> None:
    """uids are random per upload, so a uid tie-break would list the sources
    of one commodity in a new order every time the same data is uploaded."""
    cs = _make_changeset(test_admin_session, org_uid)

    # uids run opposite to identifiers, so a uid tie-break would list C-3 first.
    for identifier, uid_int in [("C-1", 3), ("C-2", 2), ("C-3", 1)]:
        entity = make_commodity_location_entity(
            test_admin_session,
            org_uid,
            identifier=identifier,
            commodity_subgroup="Maize (corn)",
            uid=uuid.UUID(int=uid_int),
        )
        make_creation_change(test_admin_session, org_uid, cs.uid, entity)

    results, _ = get_commodity_sources(
        test_admin_session,
        org_uid,
        cs.uid,
        sort_on="commodity_subgroup",
        sort_order=sort_order,
    )

    # The tie-break is ascending whichever way the primary column sorts.
    assert [r.identifier for r in results] == ["C-1", "C-2", "C-3"]


@pytest.mark.parametrize("sort_order", [SortOrder.ASC, SortOrder.DESC])
def test_get_commodity_sources_breaks_ties_on_country_region_supplier_product(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    sort_order: SortOrder,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    """Sources of one commodity list by country, then region, supplier and
    product, before falling back to the identifier - paging included, since
    country and region are extra sort columns the cursor has to carry."""
    cs = _make_changeset(test_admin_session, org_uid)

    # Identifiers run opposite to the expected order, so an identifier
    # tie-break alone would list C-1 first. Each row differs from the one
    # before it in exactly one tie-break column.
    for identifier, country, region, supplier, product in [
        ("C-5", "Australia", "Victoria", "Supplier A", "Product A"),
        ("C-4", "Australia", "Victoria", "Supplier A", "Product B"),
        ("C-3", "Australia", "Victoria", "Supplier B", "Product A"),
        ("C-2", "Australia", "Western Australia", "Supplier A", "Product A"),
        ("C-1", "South Africa", "Victoria", "Supplier A", "Product A"),
    ]:
        entity = make_commodity_location_entity(
            test_admin_session,
            org_uid,
            identifier=identifier,
            commodity_subgroup="Apples",
            supplier=supplier,
            product=product,
        )
        make_creation_change(test_admin_session, org_uid, cs.uid, entity)
        make_exported_commodity_location(
            test_admin_session,
            org_uid,
            entity.uid,
            identifier=identifier,
            sourcing_country_name=country,
            sourcing_administrative_level_1_name=region,
            change_set_uid=cs.uid,
        )

    seen: list[str] = []
    cursor = None
    for _ in range(5):
        rows, paginator = get_commodity_sources(
            test_admin_session,
            org_uid,
            cs.uid,
            sort_on="commodity_subgroup",
            sort_order=sort_order,
            cursor=cursor,
            limit=2,
        )
        seen.extend(row.identifier for row in rows)
        cursor = paginator.get_next_cursor()
        if cursor is None or not rows:
            break

    # The tie-breaks are ascending whichever way the primary column sorts.
    assert seen == ["C-5", "C-4", "C-3", "C-2", "C-1"]


@pytest.fixture
def make_commodity_survivor_and_departed(
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> Callable[
    ..., tuple[ChangeSet, CommodityLocationEntity, CommodityLocationEntity]
]:
    def _make_commodity_survivor_and_departed(
        session: SafeSession, org_uid: uuid.UUID
    ) -> tuple[ChangeSet, CommodityLocationEntity, CommodityLocationEntity]:
        """Two commodities created in cs1; one tombstoned in its child cs2.

        Mirrors `_survivor_and_departed` in test_site.py.
        """
        cs1 = _make_changeset(session, org_uid)

        survivor = make_commodity_location_entity(
            session, org_uid, identifier="C-KEEP"
        )
        departed = make_commodity_location_entity(
            session, org_uid, identifier="C-GONE"
        )
        for entity in (survivor, departed):
            make_creation_change(session, org_uid, cs1.uid, entity)
        make_exported_commodity_location(
            session,
            org_uid,
            survivor.uid,
            identifier="C-KEEP",
            sourcing_country_name="Germany",
            change_set_uid=cs1.uid,
        )
        make_exported_commodity_location(
            session,
            org_uid,
            departed.uid,
            identifier="C-GONE",
            sourcing_country_name="Japan",
            change_set_uid=cs1.uid,
        )

        cs2 = _make_changeset(session, org_uid, parent_uid=cs1.uid)
        _register_tombstone(session, org_uid, cs2.uid, departed)
        return cs2, survivor, departed

    return _make_commodity_survivor_and_departed


def test_get_commodity_sources_scope_alive_is_the_default(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_survivor_and_departed: Callable[
        ..., tuple[ChangeSet, CommodityLocationEntity, CommodityLocationEntity]
    ],
) -> None:
    cs2, survivor, _ = make_commodity_survivor_and_departed(
        test_admin_session, org_uid
    )

    defaulted, _ = get_commodity_sources(test_admin_session, org_uid, cs2.uid)
    explicit, _ = get_commodity_sources(
        test_admin_session, org_uid, cs2.uid, scope=EntityScope.ALIVE
    )

    assert [c.entity_uid for c in defaulted] == [survivor.uid]
    assert [c.entity_uid for c in explicit] == [survivor.uid]
    assert all(source.alive_in_change_set for source in defaulted)


def test_get_commodity_sources_scope_all_returns_entities_not_in_changeset(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_survivor_and_departed: Callable[
        ..., tuple[ChangeSet, CommodityLocationEntity, CommodityLocationEntity]
    ],
) -> None:
    cs2, survivor, departed = make_commodity_survivor_and_departed(
        test_admin_session, org_uid
    )

    results, paginator = get_commodity_sources(
        test_admin_session, org_uid, cs2.uid, scope=EntityScope.ALL
    )

    by_uid = {source.entity_uid: source for source in results}
    assert set(by_uid) == {survivor.uid, departed.uid}
    assert paginator.total_count == 2
    assert by_uid[survivor.uid].alive_in_change_set is True
    assert by_uid[departed.uid].alive_in_change_set is False
    # Last known values, not blanks.
    assert by_uid[departed.uid].sourcing_country == "Japan"


def test_get_commodity_sources_scope_all_filters_cover_departed_entities(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_survivor_and_departed: Callable[
        ..., tuple[ChangeSet, CommodityLocationEntity, CommodityLocationEntity]
    ],
) -> None:
    """A country filter must not silently drop rows outside the version."""
    cs2, _, departed = make_commodity_survivor_and_departed(
        test_admin_session, org_uid
    )

    results, _ = get_commodity_sources(
        test_admin_session,
        org_uid,
        cs2.uid,
        countries=["Japan"],
        scope=EntityScope.ALL,
    )

    assert [c.entity_uid for c in results] == [departed.uid]
    assert results[0].alive_in_change_set is False


def test_get_commodity_sources_scope_all_keeps_entity_with_no_exported_row(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)
    orphan = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C-ORPHAN"
    )
    make_creation_change(test_admin_session, org_uid, cs.uid, orphan)

    results, _ = get_commodity_sources(
        test_admin_session, org_uid, cs.uid, scope=EntityScope.ALL
    )

    row = next(c for c in results if c.entity_uid == orphan.uid)
    assert row.sourcing_country is None
    assert row.sourcing_region is None
    assert row.spend is None
    assert row.quantity_kilograms is None


def test_get_commodity_sources_scope_all_paginates_past_null_sort_values(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> None:
    """Sorting on a nullable export column must not drop rows at the boundary.

    Paginator coalesces NULLs out of a sort column only when the column
    reports `nullable`. A hand-built VALUES `column()` does not, so the
    coalescing was skipped, the keyset comparison compared against NULL and
    matched nothing, and the second page came back empty -- silently, with
    no error. Two of the four rows below were unreachable.

    DESC puts the NULLs first, so the page-one boundary row carries one.
    """
    cs = _make_changeset(test_admin_session, org_uid)
    for i, quantity in enumerate([None, None, 10.0, 20.0]):
        entity = make_commodity_location_entity(
            test_admin_session,
            org_uid,
            identifier=f"C{i}",
            normalised_key=f"c{i}",
        )
        make_creation_change(test_admin_session, org_uid, cs.uid, entity)
        make_exported_commodity_location(
            test_admin_session,
            org_uid,
            entity.uid,
            identifier=f"C{i}",
            quantity_kilograms=quantity,
            spend=1.0,
            change_set_uid=cs.uid,
        )

    seen: list[str] = []
    cursor = None
    for _ in range(4):
        rows, paginator = get_commodity_sources(
            test_admin_session,
            org_uid,
            cs.uid,
            scope=EntityScope.ALL,
            sort_on="quantity_kilograms",
            cursor=cursor,
            limit=2,
        )
        seen.extend(row.identifier for row in rows)
        cursor = paginator.get_next_cursor()
        if cursor is None or not rows:
            break

    assert sorted(seen) == ["C0", "C1", "C2", "C3"]


# ---------------------------------------------------------------------------
# get_aggregated_commodity_regions
# ---------------------------------------------------------------------------


def _square(offset: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [offset, offset],
                [offset + 1, offset],
                [offset + 1, offset + 1],
                [offset, offset + 1],
                [offset, offset],
            ]
        ],
    }


def _make_admin_region(
    session: SafeSession,
    *,
    level: AdminRegionLevel,
    name: str,
    country_name: str,
    country_code: str,
) -> AdminRegion:
    region = AdminRegion(
        level=level,
        name=name,
        country_name=country_name,
        country_code=country_code,
        geojson=_square(0.0),
        geojson_simplified=_square(0.5),
    )
    session.add(region)
    session.flush()
    return region


@pytest.fixture
def make_alive_commodity_in_region(
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_exported_commodity_location: Callable[..., ExportedCommodityLocation],
) -> Callable[..., CommodityLocationEntity]:
    def _make_alive_commodity_in_region(
        session: SafeSession,
        org_uid: uuid.UUID,
        cs: ChangeSet,
        *,
        identifier: str,
        commodity_subgroup: str,
        admin_region: AdminRegion | None,
        spend: float | None,
        quantity_kilograms: float | None,
        sourcing_country_name: str | None = None,
        sourcing_administrative_level_1_name: str | None = None,
    ) -> CommodityLocationEntity:
        entity = make_commodity_location_entity(
            session,
            org_uid,
            identifier=identifier,
            commodity_subgroup=commodity_subgroup,
        )
        entity.sourcing_admin_region_uid = (
            admin_region.uid if admin_region is not None else None
        )
        session.flush()
        make_creation_change(session, org_uid, cs.uid, entity)
        make_exported_commodity_location(
            session,
            org_uid,
            entity.uid,
            identifier=identifier,
            commodity_subgroup=commodity_subgroup,
            sourcing_country_name=sourcing_country_name,
            sourcing_administrative_level_1_name=sourcing_administrative_level_1_name,
            spend=spend,
            quantity_kilograms=quantity_kilograms,
            change_set_uid=cs.uid,
        )
        return entity

    return _make_alive_commodity_in_region


def test_get_aggregated_commodity_regions_groups_by_admin_region(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_alive_commodity_in_region: Callable[..., CommodityLocationEntity],
) -> None:
    """Locations come from the entity's sourcing_admin_region_uid: a REGION
    row names its admin-1 region, a COUNTRY row has none. Subgroups sharing a
    location fold into one row with a per-subgroup breakdown."""
    cs = _make_changeset(test_admin_session, org_uid)
    sao_paulo = _make_admin_region(
        test_admin_session,
        level=AdminRegionLevel.REGION,
        name="Sao Paulo",
        country_name="Brazil",
        country_code="BR",
    )
    brazil = _make_admin_region(
        test_admin_session,
        level=AdminRegionLevel.COUNTRY,
        name="Brazil",
        country_name="Brazil",
        country_code="BR",
    )
    for identifier, subgroup, region, spend, quantity in (
        ("C1", "Coffee", sao_paulo, 100.0, 10.0),
        ("C2", "Coffee", sao_paulo, 50.0, None),
        ("C3", "Cocoa", sao_paulo, 25.0, 5.0),
        ("C4", "Coffee", brazil, 7.0, 3.0),
    ):
        make_alive_commodity_in_region(
            test_admin_session,
            org_uid,
            cs,
            identifier=identifier,
            commodity_subgroup=subgroup,
            admin_region=region,
            spend=spend,
            quantity_kilograms=quantity,
        )

    regions = get_aggregated_commodity_regions(
        test_admin_session, org_uid, cs.uid
    )

    assert [
        (r.country_name, r.sourcing_administrative_level_1_name)
        for r in regions
    ] == [("Brazil", "Sao Paulo"), ("Brazil", None)]
    region, country = regions
    assert region.total_spend == 175.0
    assert region.total_quantity == 15.0
    assert [
        (b.commodity_subgroup, b.total_spend, b.total_quantity)
        for b in region.commodity_breakdown
    ] == [("Cocoa", 25.0, 5.0), ("Coffee", 150.0, 10.0)]
    assert country.total_spend == 7.0
    # Geometry is opt-in.
    assert region.geometry is None


def test_get_aggregated_commodity_regions_group_by_country_sums_regions(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_alive_commodity_in_region: Callable[..., CommodityLocationEntity],
) -> None:
    """`group_by_country` folds admin-1 regions into their country's row,
    which takes the COUNTRY-level geometry - also for a country named only
    through its regions."""
    cs = _make_changeset(test_admin_session, org_uid)
    victoria = _make_admin_region(
        test_admin_session,
        level=AdminRegionLevel.REGION,
        name="Victoria",
        country_name="Australia",
        country_code="AU",
    )
    australia = _make_admin_region(
        test_admin_session,
        level=AdminRegionLevel.COUNTRY,
        name="Australia",
        country_name="Australia",
        country_code="AU",
    )
    australia.geojson_simplified = _square(10.0)
    northern_cape = _make_admin_region(
        test_admin_session,
        level=AdminRegionLevel.REGION,
        name="Northern Cape",
        country_name="South Africa",
        country_code="ZA",
    )
    south_africa = _make_admin_region(
        test_admin_session,
        level=AdminRegionLevel.COUNTRY,
        name="South Africa",
        country_name="South Africa",
        country_code="ZA",
    )
    south_africa.geojson_simplified = _square(20.0)
    test_admin_session.flush()
    for identifier, subgroup, region, spend, quantity in (
        ("C1", "Apples", victoria, 100.0, 10.0),
        ("C2", "Oranges", australia, 50.0, 5.0),
        ("C3", "Apples", australia, 7.0, 3.0),
        ("C4", "Apples", northern_cape, 25.0, 2.0),
    ):
        make_alive_commodity_in_region(
            test_admin_session,
            org_uid,
            cs,
            identifier=identifier,
            commodity_subgroup=subgroup,
            admin_region=region,
            spend=spend,
            quantity_kilograms=quantity,
        )

    regions = get_aggregated_commodity_regions(
        test_admin_session,
        org_uid,
        cs.uid,
        include_geometry=True,
        group_by_country=True,
    )

    assert [
        (r.country_name, r.sourcing_administrative_level_1_name)
        for r in regions
    ] == [("Australia", None), ("South Africa", None)]
    au, za = regions
    assert au.total_spend == 157.0
    assert au.total_quantity == 18.0
    assert [
        (b.commodity_subgroup, b.total_spend, b.total_quantity)
        for b in au.commodity_breakdown
    ] == [("Apples", 107.0, 13.0), ("Oranges", 50.0, 5.0)]
    assert au.geometry is not None
    assert au.geometry.model_dump(mode="json") == _square(10.0)
    assert za.total_spend == 25.0
    assert za.geometry is not None
    assert za.geometry.model_dump(mode="json") == _square(20.0)


def test_get_aggregated_commodity_regions_include_geometry_prefers_simplified(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_alive_commodity_in_region: Callable[..., CommodityLocationEntity],
) -> None:
    cs = _make_changeset(test_admin_session, org_uid)
    sao_paulo = _make_admin_region(
        test_admin_session,
        level=AdminRegionLevel.REGION,
        name="Sao Paulo",
        country_name="Brazil",
        country_code="BR",
    )
    make_alive_commodity_in_region(
        test_admin_session,
        org_uid,
        cs,
        identifier="C1",
        commodity_subgroup="Coffee",
        admin_region=sao_paulo,
        spend=100.0,
        quantity_kilograms=10.0,
    )

    [region] = get_aggregated_commodity_regions(
        test_admin_session, org_uid, cs.uid, include_geometry=True
    )

    assert region.geometry is not None
    assert region.geometry.model_dump(mode="json") == _square(0.5)


def test_get_aggregated_commodity_regions_unresolved_region_falls_back_to_export_names(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_alive_commodity_in_region: Callable[..., CommodityLocationEntity],
) -> None:
    """An entity whose names matched no AdminRegion still counts, under its
    export row's names and without geometry - as the v1 query did."""
    cs = _make_changeset(test_admin_session, org_uid)
    make_alive_commodity_in_region(
        test_admin_session,
        org_uid,
        cs,
        identifier="C1",
        commodity_subgroup="Coffee",
        admin_region=None,
        spend=100.0,
        quantity_kilograms=10.0,
        sourcing_country_name="Atlantis",
        sourcing_administrative_level_1_name="Lost City",
    )

    [region] = get_aggregated_commodity_regions(
        test_admin_session, org_uid, cs.uid, include_geometry=True
    )

    assert region.country_name == "Atlantis"
    assert region.sourcing_administrative_level_1_name == "Lost City"
    assert region.total_spend == 100.0
    assert region.geometry is None


def test_get_aggregated_commodity_regions_reads_only_the_changeset(
    set_up_test_db: None,
    test_admin_session: SafeSession,
    org_uid: uuid.UUID,
    make_commodity_location_entity: Callable[..., CommodityLocationEntity],
    make_creation_change: Callable[..., Change],
    make_alive_commodity_in_region: Callable[..., CommodityLocationEntity],
) -> None:
    """A tombstoned entity drops out, and an alive entity with no export row
    in the changeset contributes nothing."""
    parent = _make_changeset(test_admin_session, org_uid)
    make_alive_commodity_in_region(
        test_admin_session,
        org_uid,
        parent,
        identifier="C-KEPT",
        commodity_subgroup="Coffee",
        admin_region=None,
        spend=10.0,
        quantity_kilograms=1.0,
        sourcing_country_name="France",
    )
    removed = make_alive_commodity_in_region(
        test_admin_session,
        org_uid,
        parent,
        identifier="C-REMOVED",
        commodity_subgroup="Cocoa",
        admin_region=None,
        spend=99.0,
        quantity_kilograms=9.0,
        sourcing_country_name="Ghana",
    )
    child = _make_changeset(test_admin_session, org_uid, parent_uid=parent.uid)
    _register_tombstone(test_admin_session, org_uid, child.uid, removed)
    unexported = make_commodity_location_entity(
        test_admin_session, org_uid, identifier="C-UNEXPORTED"
    )
    make_creation_change(test_admin_session, org_uid, child.uid, unexported)

    regions = get_aggregated_commodity_regions(
        test_admin_session, org_uid, child.uid
    )

    assert [(r.country_name, r.total_spend) for r in regions] == [
        ("France", 10.0)
    ]
