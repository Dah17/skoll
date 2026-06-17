import typing as t

from attrs import define, field
from abc import ABC, abstractmethod
from skoll.utils.functional import parse_db_cursor

from .primitives import ID

__all__ = ["Criteria", "ListPage", "SQLCriteria", "DecodedJwtToken", "KVBucket"]


class ListPage[T](t.NamedTuple):

    items: list[T]
    cursor: str | None = None


class KVBucket(t.NamedTuple):

    key: str
    ttl: int | None = None


class DecodedJwtToken(t.NamedTuple):

    expired: bool = False
    invalid: bool = False
    sub: str | None = None
    kind: str | None = None
    extra: dict[str, t.Any] | None = None


class SQLCriteria(t.NamedTuple):
    query: str
    params: list[t.Any]
    count_query: str
    count_params: list[t.Any]
    items_count: int | None = None

    @classmethod
    def new(cls, crt: "Criteria", attrs: list[tuple[str, t.Any]], table: str, prefix: str = "SELECT *") -> t.Self:
        cursor = parse_db_cursor(crt.cursor) if crt.cursor else None
        if crt.id is not None:
            attrs.append((f"id = ${len(attrs) + 1}", crt.id.value))
        if crt.id is None and cursor is not None and cursor.id is not None:
            attrs.append((f"id >= ${len(attrs) + 1}", cursor.id))

        where_clause = " AND ".join(attr[0] for attr in attrs) if len(attrs) > 0 else "1=1"
        query = f"{prefix} FROM {table} WHERE {where_clause} ORDER BY id ASC LIMIT ${len(attrs) + 1}"
        count_params = [value for _, value in attrs]
        params = count_params + [crt.limit + 1]
        count_query = f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"
        return cls(query, params, count_query, count_params=count_params, items_count=cursor.count if cursor else None)


@define(frozen=True, kw_only=True, slots=True)
class Criteria(ABC):

    id: ID | None = None
    cursor: str | None = None
    limit: int = field(default=150)

    @property
    @abstractmethod
    def as_sql(self) -> SQLCriteria:
        raise NotImplementedError("Subclasses must implement this method")
