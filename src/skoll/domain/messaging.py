import typing as t
import collections.abc as c

from attrs import define, field
from skoll.result import is_ok, Result
from skoll.exceptions import InternalError


from .primitives import Object, ID, DateTime, Locale, Map, Timezone

__all__ = [
    "Service",
    "Message",
    "Services",
    "MsgClient",
    "RawMessage",
    "MsgContext",
    "Subscriber",
    "RawMsgClient",
    "RawMsgContext",
    "MsgClientDevice",
    "RawMsgClientDevice",
    "SubscriberCallback",
]

type SubscriberCallback = t.Callable[..., c.Coroutine[t.Any, t.Any, Result[t.Any]]]


class RawMsgClientDevice(t.TypedDict):
    duid: t.NotRequired[str]
    model: t.NotRequired[str]
    brand: t.NotRequired[str]
    os_name: t.NotRequired[str]
    os_version: t.NotRequired[str]


class RawMsgClient(t.TypedDict):
    ip_address: t.NotRequired[str]
    locale: t.NotRequired[str]
    timezone: t.NotRequired[str]
    device: t.NotRequired[RawMsgClientDevice]


class RawMsgContext(t.TypedDict):
    user_id: t.NotRequired[str]
    span_id: t.NotRequired[str]
    trace_id: t.NotRequired[str]
    client: t.NotRequired[RawMsgClient]
    extra: t.NotRequired[dict[str, t.Any]]


class RawMessage(t.TypedDict):
    name: str
    source: str
    id: t.NotRequired[str]
    created_at: t.NotRequired[int]
    context: t.NotRequired[RawMsgContext]
    payload: t.NotRequired[dict[str, t.Any]]


@define(frozen=True, kw_only=True, slots=True)
class MsgClientDevice(Object):

    duid: ID | None = None
    model: str | None = None
    brand: str | None = None
    os_name: str | None = None
    os_version: str | None = None


@define(frozen=True, kw_only=True, slots=True)
class MsgClient(Object):

    ip_address: str | None = None
    locale: Locale = field(factory=Locale)
    timezone: Timezone = field(factory=Timezone)
    device: MsgClientDevice = field(factory=MsgClientDevice)


@define(frozen=True, kw_only=True, slots=True)
class MsgContext(Object):

    user_id: ID | None = None
    extra: Map = field(factory=Map)
    span_id: ID = field(factory=ID)
    trace_id: ID = field(factory=ID)
    client: MsgClient = field(factory=MsgClient)


@define(frozen=True, kw_only=True, slots=True, eq=False)
class Message(Object):

    name: str
    source: str
    id: ID = field(factory=ID)
    payload: Map = field(factory=Map)
    context: MsgContext = field(factory=MsgContext)
    created_at: DateTime = field(factory=DateTime.now)

    def unwrap_payload[T: Object](self, cls: type[T]) -> T:
        res = cls.create(self.payload.value)
        if not is_ok(res):
            raise InternalError(debug={"message": "Failed to unwrap payload"})
        return res.value

    @t.override
    def __eq__(self, other: t.Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return other.__hash__() == self.__hash__()

    @t.override
    def __ne__(self, other: t.Any) -> bool:
        return not self == other

    @t.override
    def __hash__(self) -> int:
        return hash(self.id.serialize())

    @classmethod
    def from_raw(cls, raw: RawMessage) -> t.Self | None:
        res = cls.create(raw)
        if is_ok(res):
            return res.value
        return None


@define(frozen=True, kw_only=True, slots=True)
class Subscriber:

    topic: str
    queued: bool
    will_reply: bool
    service_name: str
    js_stream: str | None = None
    callback: SubscriberCallback


@define(kw_only=True, slots=True, frozen=True)
class Service:

    name: str
    subscribers: list[Subscriber] = field(factory=list)

    def _add(
        self, topic: str, will_reply: bool, queued: bool, callback: SubscriberCallback, js_stream: str | None = None
    ):
        self.subscribers.append(
            Subscriber(
                topic=topic,
                queued=queued,
                callback=callback,
                js_stream=js_stream,
                will_reply=will_reply,
                service_name=self.name,
            )
        )

    def on(self, topic: str, queued: bool = False, stream: str | None = None):
        def decorator(callback: SubscriberCallback):
            self._add(topic, will_reply=False, queued=queued, callback=callback, js_stream=stream)
            return callback

        return decorator

    def reply(self, topic: str):
        def decorator(callback: SubscriberCallback):
            self._add(topic, will_reply=True, queued=True, callback=callback)
            return callback

        return decorator


@define(frozen=True, kw_only=True, slots=True)
class Services:

    items: list[Service] = field(factory=list)

    def extend(self, service: list[Service] | list[t.Self]):
        for item in service:
            if isinstance(item, Services):
                self.items.extend(item.items)
            else:
                self.items.append(item)

    def __add__(self, other: t.Self | Service):
        return Services(items=self.items + (other.items if isinstance(other, Services) else [other]))

    def __radd__(self, other: t.Self | Service):
        return Services(items=(other.items if isinstance(other, Services) else [other]) + self.items)
