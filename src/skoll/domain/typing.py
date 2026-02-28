import typing as t

from attrs import define, field
from abc import ABC, abstractmethod

from .primitives import ID, DateTime


__all__ = [
    "Criteria",
    "ListPage",
    "SQLCriteria",
    "ListCriteria",
    "DecodedJwtToken",
    "AuthzWriteChange",
    "AuthzPrecondition",
    "AuthzLookupResult",
    "AuthzWriteOperation",
    "AuthzPreconditionOperation",
]

type AuthzWriteOperation = t.Literal["SET", "DELETE"]
type AuthzPrecondition = tuple[AuthzPreconditionOperation, str]
type AuthzPreconditionOperation = t.Literal["MUST_MATCH", "MUST_NOT_MATCH"]
type AuthzWriteChange = tuple[AuthzWriteOperation, str, tuple[str, dict[str, t.Any]] | None, DateTime | None]


class ListPage[T](t.NamedTuple):

    items: list[T]
    cursor: str | None = None


class SQLCriteria(t.NamedTuple):
    query: str
    params: list[t.Any]


class DecodedJwtToken(t.NamedTuple):

    expired: bool = False
    invalid: bool = False
    sub: str | None = None
    kind: str | None = None
    extra: dict[str, t.Any] | None = None


@define(frozen=True, kw_only=True, slots=True)
class Criteria(ABC):

    id: ID | None = None

    @property
    @abstractmethod
    def as_sql(self) -> SQLCriteria:
        raise NotImplementedError("Subclasses must implement this method")


@define(frozen=True, kw_only=True, slots=True)
class ListCriteria(Criteria, ABC):

    cursor: str | None = None
    limit: int = field(default=150)


class AuthzLookupResult(t.NamedTuple):
    ids: list[str]
    cursor: str | None = None
