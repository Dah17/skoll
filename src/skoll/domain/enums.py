from .primitives import Enum

__all__ = ["SortDirection", "Status", "ThemeMode", "UnitSystem"]


class SortDirection(Enum):

    ASCENDING = "ASC"
    DESCENDING = "DESC"


class Status(Enum):

    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class ThemeMode(Enum):

    DARK = "DARK"
    LIGHT = "LIGHT"
    SYSTEM = "SYSTEM"


class UnitSystem(Enum):

    METRIC = "METRIC"
    IMPERIAL = "IMPERIAL"
    US_CUSTOMARY = "US_CUSTOMARY"
