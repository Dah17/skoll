import typing as t
import collections.abc as c

from attrs import define, field
from skoll.result import is_ok, Result
from inspect import iscoroutinefunction, signature


from .primitives import Object, ID, DateTime, Locale, Map, Timezone

__all__ = [
    "Service",
    "Message",
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

type SubscriberCallback[T: Message] = t.Callable[t.Concatenate[T, ...], c.Coroutine[t.Any, t.Any, Result[t.Any]]]


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

    @classmethod
    def default(cls) -> t.Self:
        return cls()


@define(frozen=True, kw_only=True, slots=True)
class MsgClient(Object):

    ip_address: str | None = None
    locale: Locale = field(factory=Locale.default)
    timezone: Timezone = field(factory=Timezone.default)
    device: MsgClientDevice = field(factory=MsgClientDevice.default)

    @classmethod
    def default(cls) -> t.Self:
        return cls()


@define(frozen=True, kw_only=True, slots=True)
class MsgContext(Object):

    user_id: ID | None = None
    span_id: ID = field(factory=ID.new)
    trace_id: ID = field(factory=ID.new)
    extra: Map = field(factory=Map.empty)
    client: MsgClient = field(factory=MsgClient.default)

    @classmethod
    def default(cls) -> t.Self:
        return cls()


@define(frozen=True, kw_only=True, slots=True, eq=False)
class Message(Object):

    name: str
    source: str
    payload: Object
    id: ID = field(factory=ID.new)
    created_at: DateTime = field(factory=DateTime.now)
    context: MsgContext = field(factory=MsgContext.default)

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
