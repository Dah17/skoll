from .base import Enum

__all__ = ["SortDirection", "Status"]


class SortDirection(Enum):

    ASCENDING = "ASC"
    DESCENDING = "DESC"


class Status(Enum):

    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"
