from src.backend.app.util.enums import (
    ChangeSetState,
    SortOrder,
    is_completed_state,
)


def test_sort_order_reverse():
    assert -SortOrder.DESC == SortOrder.ASC
    assert -SortOrder.ASC == SortOrder.DESC


def test_base_enum_contains():
    """Test the __contains__ operator for BaseEnum via MetaEnum."""
    assert "asc" in SortOrder
    assert "desc" in SortOrder
    assert "invalid" not in SortOrder


def test_is_completed_state():
    """Test the is_completed_state function."""
    assert is_completed_state(ChangeSetState.DONE)
    assert is_completed_state(ChangeSetState.PUBLISHED)
    assert not is_completed_state(ChangeSetState.DRAFT)
    assert not is_completed_state(ChangeSetState.PROCESSING)
