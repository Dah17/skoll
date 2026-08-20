import typing as t
import collections.abc as c

from attrs import define, field
from skoll.result import Result


from .primitives import Object, ID, DateTime, Map, Ulid

type SubscriberAccess = t.Literal["PUBLIC", "PRIVATE", "INTERNAL"]
type SubscriberCallback = t.Callable[..., c.Coroutine[t.Any, t.Any, Result[t.Any]]]

EMPTY_MAP: Map = Map()


@define(frozen=True, kw_only=True, slots=True, eq=False)
class Message(Object):

    subject: str
    id: ID = field(factory=Ulid)
    cxt: Map = field(factory=Map)
    payload: Map = field(factory=Map)
    created_at: DateTime = field(factory=DateTime.now)

    @classmethod
    def new(
        cls, subject: str, payload: dict[str, t.Any] | Map = EMPTY_MAP, cxt: dict[str, t.Any] | Map = EMPTY_MAP
    ) -> t.Self:
        payload = Map(value=payload) if isinstance(payload, dict) else payload
        cxt = Map(value=cxt) if isinstance(cxt, dict) else cxt
        return cls(subject=subject, payload=payload, cxt=cxt)

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


@define(frozen=True, kw_only=True, slots=True)
class Subscriber:

    subject: str
    queued: bool
    will_reply: bool
    service_name: str
    access: SubscriberAccess
    js_stream: str | None = None
    callback: SubscriberCallback
    payload_key: str | None = None


@define(kw_only=True, slots=True, frozen=True)
class Service:

    name: str
    subscribers: list[Subscriber] = field(factory=list)

    def subjects(self, filters: list[SubscriberAccess]) -> list[str]:
        return [sub.subject for sub in self.subscribers if sub.access in filters]

    def _add(
        self,
        subject: str,
        will_reply: bool,
        queued: bool,
        callback: SubscriberCallback,
        access: SubscriberAccess,
        js_stream: str | None = None,
        payload_key: str | None = None,
    ):
        self.subscribers.append(
            Subscriber(
                queued=queued,
                subject=subject,
                callback=callback,
                js_stream=js_stream,
                will_reply=will_reply,
                service_name=self.name,
                payload_key=payload_key,
                access=access or "PRIVATE",
            )
        )

    def on(self, subject: str, payload_key: str | None = None, queued: bool = False, stream: str | None = None):
        def decorator(callback: SubscriberCallback):
            self._add(
                subject,
                will_reply=False,
                queued=queued,
                callback=callback,
                access="PRIVATE",
                js_stream=stream,
                payload_key=payload_key,
            )
            return callback

        return decorator

    def reply(self, subject: str, payload_key: str | None = None, access: SubscriberAccess = "PRIVATE"):
        def decorator(callback: SubscriberCallback):
            self._add(subject, will_reply=True, queued=True, callback=callback, access=access, payload_key=payload_key)
            return callback

        return decorator


@define(frozen=True, kw_only=True, slots=True)
class Services:

    items: list[Service] = field(factory=list)

    def subjects(self, filters: list[SubscriberAccess]) -> list[str]:
        return [sub for s in self.items for sub in s.subjects(filters)]

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


__all__ = ["Service", "Message", "Services", "Subscriber", "SubscriberAccess", "SubscriberCallback"]
