from .base import Enum

__all__ = ["SortDirection", "EntityStatus"]


class SortDirection(Enum):

    ASCENDING = "ASC"
    DESCENDING = "DESC"


class EntityStatus(Enum):

    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"
