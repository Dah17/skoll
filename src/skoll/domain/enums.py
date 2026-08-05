from .primitives import Enum

__all__ = ["SortDirection"]


class SortDirection(Enum):

    ASCENDING = "ASC"
    DESCENDING = "DESC"
