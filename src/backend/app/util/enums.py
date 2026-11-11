import enum
from typing import Any


class MetaEnum(enum.EnumMeta):
    """
    The meta class for the wrapper around the standard enum.Enum. Enables use of the
    "in" operator to check if a value is a valid member of the enum.
    """

    def __contains__(cls, item: Any) -> bool:
        try:
            cls(item)
        except ValueError:
            return False
        return True


class BaseEnum(enum.Enum, metaclass=MetaEnum):
    """
    The wrapper class that implements the MetaEnum meta class to enable the "in" operator.
    Should be inherited by all enums in the application.
    """

    pass


class EntityScope(BaseEnum):
    """Which entities a changeset-aware listing returns.

    ALIVE: only entities alive in the requested changeset (the default).
    ALL: every entity in the organisation, each carrying
    `alive_in_change_set` so a caller can show the rest as not in this
    version rather than omitting them.
    """

    ALIVE = "alive"
    ALL = "all"


class SortOrder(BaseEnum):
    ASC = "asc"
    DESC = "desc"

    def __neg__(self) -> "SortOrder":
        return SortOrder.ASC if self == SortOrder.DESC else SortOrder.DESC


class ChangeSetState(BaseEnum):
    DRAFT = "draft"
    PROCESSING = "processing"
    DONE = "done"
    PUBLISHED = "published"


def is_completed_state(state: ChangeSetState) -> bool:
    return state in {ChangeSetState.DONE, ChangeSetState.PUBLISHED}


class DataCoverage(str, BaseEnum):
    """How many of a change set's entities have a value, such as commodity
    locations with spend: all, some or none."""

    FULL = "FULL"
    PARTIAL = "PARTIAL"
    NONE = "NONE"


class AdminRegionLevel(str, BaseEnum):
    COUNTRY = "country"
    REGION = "region"
    SUBREGION = "subregion"


class UnitOfAnalysis(enum.Enum):
    """Unit of analysis for change summaries."""

    COMMODITY_SOURCE = "commodity_source"
