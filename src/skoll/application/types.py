import typing as t
from attrs import define, field
from abc import ABC, abstractmethod

from skoll.domain import ID


__all__ = ["Criteria", "ListPage", "ListCriteria"]


class ListPage[T](t.NamedTuple):

    items: list[T]
    cursor: str | None = None


class SQLCriteria(t.NamedTuple):
    query: str
    params: list[t.Any]


@define(frozen=True, kw_only=True, slots=True)
class Criteria(ABC):

    uid: ID | None = None

    @property
    @abstractmethod
    def as_sql(self) -> SQLCriteria:
        raise NotImplementedError("Subclasses must implement this method")


@define(frozen=True, kw_only=True, slots=True)
class ListCriteria(Criteria, ABC):

    cursor: str | None = None
    limit: int = field(default=100)


# type AuthzWriteOperation = t.Literal["SET", "DELETE"]
# type AuthzPrecondition = tuple[AuthzPreconditionOperation, str]
# type AuthzPreconditionOperation = t.Literal["MUST_MATCH", "MUST_NOT_MATCH"]
# type SubscriberCallback = t.Callable[t.Concatenate[Message, ...], c.Coroutine[t.Any, t.Any, Result[t.Any]]]
# type AuthzWriteChange = tuple[AuthzWriteOperation, str, tuple[str, dict[str, t.Any]] | None, DateTime | None]


# class AuthzLookupResult(t.NamedTuple):
#     uids: list[str]
#     cursor: str | None = None

# class RawMessage(t.TypedDict):
#     topic: str
#     source: str
#     id: t.NotRequired[str]
#     created_at: t.NotRequired[int]
#     payload: t.NotRequired[dict[str, t.Any]]
#     context: t.NotRequired[dict[str, t.Any]]


# @define(frozen=True, kw_only=True, slots=True)
# class Subscriber:

#     topic: str
#     msg_arg: str
#     service_name: str
#     msg_cls: type[Message]
#     with_reply: bool = True
#     callback: SubscriberCallback


# @define(kw_only=True, slots=True)
# class MissingSubscriber(NotFound):

#     attr: str | None = field(default=None, init=False)
#     code: str = field(default="missing_subscriber", init=False)
#     detail: str = "No subscriber found for the given message subject"


# @define(kw_only=True, slots=True, frozen=True)
# class Service:

#     name: str
#     subscribers: list[Subscriber] = field(factory=list)

#     def on(self, topic: str, with_reply: bool = True):
#         def decorator(callback: SubscriberCallback):
#             first_arg = list(signature(callback).parameters.values())[0]
#             if not issubclass(first_arg.annotation, Message):
#                 raise TypeError(
#                     f"@service.on only allow on function with first argument being a subclass of Message, got {first_arg.annotation}"
#                 )

#             self.subscribers.append(
#                 Subscriber(
#                     topic=topic,
#                     callback=callback,
#                     with_reply=with_reply,
#                     msg_arg=first_arg.name,
#                     service_name=self.name,
#                     msg_cls=first_arg.annotation,
#                 )
#             )
#             return callback

#         return decorator
