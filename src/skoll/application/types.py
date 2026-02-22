import typing as t
import collections.abc as c

from attrs import define, field
from skoll.result import Result
from abc import ABC, abstractmethod
from skoll.domain import ID, DateTime, Message
from inspect import iscoroutinefunction, signature


__all__ = [
    "Service",
    "Criteria",
    "ListPage",
    "Subscriber",
    "ListCriteria",
    "AuthzWriteChange",
    "AuthzPrecondition",
    "AuthzLookupResult",
    "SubscriberCallback",
    "AuthzWriteOperation",
    "AuthzPreconditionOperation",
]


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


type AuthzWriteOperation = t.Literal["SET", "DELETE"]
type AuthzPrecondition = tuple[AuthzPreconditionOperation, str]
type AuthzPreconditionOperation = t.Literal["MUST_MATCH", "MUST_NOT_MATCH"]
type AuthzWriteChange = tuple[AuthzWriteOperation, str, tuple[str, dict[str, t.Any]] | None, DateTime | None]
type SubscriberCallback[T: Message] = t.Callable[t.Concatenate[T, ...], c.Coroutine[t.Any, t.Any, Result[t.Any]]]


class AuthzLookupResult(t.NamedTuple):
    uids: list[str]
    cursor: str | None = None


@define(frozen=True, kw_only=True, slots=True)
class Subscriber[T: Message]:

    topic: str
    msg_arg: str
    queued: bool
    will_reply: bool
    service_name: str
    msg_type: type[Message]
    js_stream: str | None = None
    callback: SubscriberCallback[T]


@define(kw_only=True, slots=True, frozen=True)
class Service:

    name: str
    subscribers: list[Subscriber[t.Any]] = field(factory=list)

    def _add[T: Message](
        self, topic: str, will_reply: bool, queued: bool, callback: SubscriberCallback[T], js_stream: str | None = None
    ):
        first_arg = list(signature(callback).parameters.values())[0]
        if not issubclass(first_arg.annotation, Message) or not iscoroutinefunction(callback):
            raise TypeError(
                f"Service subscriber @on/@reply must be a coroutine and with first argument being a subclass of Message"
            )
        self.subscribers.append(
            Subscriber(
                topic=topic,
                queued=queued,
                callback=callback,
                js_stream=js_stream,
                will_reply=will_reply,
                msg_arg=first_arg.name,
                service_name=self.name,
                msg_type=first_arg.annotation,
            )
        )

    def on(self, topic: str, queued: bool = False, stream: str | None = None):
        def decorator[T: Message](callback: SubscriberCallback[T]):
            self._add(topic, will_reply=False, queued=queued, callback=callback, js_stream=stream)
            return callback

        return decorator

    def reply(self, topic: str):
        def decorator[T: Message](callback: SubscriberCallback[T]):
            self._add(topic, will_reply=True, queued=True, callback=callback)
            return callback

        return decorator
