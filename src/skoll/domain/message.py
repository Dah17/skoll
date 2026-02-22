import typing as t
from attrs import define, field

from skoll.result import is_ok
from skoll.domain.base import Object
from skoll.domain.primitives import ID, DateTime, Locale, Map, Timezone


__all__ = [
    "Message",
    "MsgClient",
    "RawMessage",
    "MsgContext",
    "MsgPayload",
    "RawMsgClient",
    "MsgClientDevice",
    "RawMsgClientDevice",
]


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


class RawMessage(t.TypedDict):
    name: str
    source: str
    id: t.NotRequired[str]
    created_at: t.NotRequired[int]
    context: t.NotRequired[RawMsgClient]
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


@define(frozen=True, kw_only=True, slots=True)
class MsgPayload(Object):

    @classmethod
    def default(cls) -> t.Self:
        return cls()


@define(frozen=True, kw_only=True, slots=True, eq=False)
class Message(Object):

    name: str
    source: str
    id: ID = field(factory=ID.new)
    created_at: DateTime = field(factory=DateTime.now)
    payload: MsgPayload = field(factory=MsgPayload.default)
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
