import re
import typing as t
import collections.abc as c

from attrs import define, field
from skoll.result import Result


from .primitives import Object, ID, DateTime, Map, Ulid

type SubjectScope = t.Literal["PUBLIC", "INTERNAL"]
type SubscriberCallback = t.Callable[..., c.Coroutine[t.Any, t.Any, Result[t.Any]]]

SUBJECT_RE = re.compile(r"^(?P<kind>cmd|qry|evt)\.(?P<scope>internal|public)\.(?P<version>v\d+)\.(?P<tail>.+)$")

EMPTY_MAP: Map = Map()


REMOVED_ACCESS_HINT = (
    "access= was removed: a subject now carries its own scope, as"
    " <cmd|qry|evt>.<internal|public>.<version>.<domain>.<aggregate>.<action>."
    " Moving a subject between scopes is a rename, not a dual-subscribe: drain it, cut over, then"
    " delete whatever consumer is left on the old name."
)


def reject_access(access: t.Any) -> None:
    if access is None:
        return
    raise TypeError(REMOVED_ACCESS_HINT)


def subject_scope(subject: str) -> SubjectScope:
    matched = SUBJECT_RE.match(subject)
    return "PUBLIC" if matched is not None and matched.group("scope") == "public" else "INTERNAL"


def is_scoped_subject(subject: str) -> bool:
    return SUBJECT_RE.match(subject) is not None


def rescope(subject: str, scope: SubjectScope) -> str:
    matched = SUBJECT_RE.match(subject)
    if matched is None:
        return subject
    return f"{matched.group('kind')}.{scope.lower()}.{matched.group('version')}.{matched.group('tail')}"


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
    js_stream: str | None = None
    callback: SubscriberCallback
    payload_key: str | None = None
    max_deliver: int | None = None
    anonymous: bool = False

    @property
    def durable(self) -> str:
        if self.js_stream is None:
            return self.service_name
        return f"{self.service_name}_{re.sub(r'[^A-Za-z0-9_-]', '_', self.subject)}"

    @property
    def scope(self) -> SubjectScope:
        return subject_scope(self.subject)

    @property
    def is_public(self) -> bool:
        return self.scope == "PUBLIC"


@define(kw_only=True, slots=True, frozen=True)
class Service:

    name: str
    subscribers: list[Subscriber] = field(factory=list)

    def subjects(self, scopes: list[SubjectScope] | None = None) -> list[str]:
        if scopes is None:
            return [sub.subject for sub in self.subscribers]
        return [sub.subject for sub in self.subscribers if sub.scope in scopes]

    def anonymous_subjects(self) -> list[str]:
        return [sub.subject for sub in self.subscribers if sub.anonymous]

    def _add(
        self,
        subject: str,
        will_reply: bool,
        queued: bool,
        callback: SubscriberCallback,
        js_stream: str | None = None,
        payload_key: str | None = None,
        max_deliver: int | None = None,
        anonymous: bool = False,
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
                max_deliver=max_deliver,
                anonymous=anonymous,
            )
        )

    def on(
        self,
        subject: str,
        queued: bool = False,
        stream: str | None = None,
        payload_key: str | None = None,
        max_deliver: int | None = None,
        anonymous: bool = False,
        access: t.Any = None,
    ):
        reject_access(access)

        def decorator(callback: SubscriberCallback):
            self._add(
                subject,
                queued=queued,
                js_stream=stream,
                will_reply=False,
                callback=callback,
                payload_key=payload_key,
                max_deliver=max_deliver,
                anonymous=anonymous,
            )
            return callback

        return decorator

    def reply(
        self,
        subject: str,
        payload_key: str | None = None,
        anonymous: bool = False,
        access: t.Any = None,
    ):
        reject_access(access)

        def decorator(callback: SubscriberCallback):
            self._add(
                subject,
                will_reply=True,
                queued=True,
                callback=callback,
                payload_key=payload_key,
                anonymous=anonymous,
            )
            return callback

        return decorator


@define(frozen=True, kw_only=True, slots=True)
class Services:

    items: list[Service] = field(factory=list)

    def subjects(self, scopes: list[SubjectScope] | None = None) -> list[str]:
        return [sub for s in self.items for sub in s.subjects(scopes)]

    def anonymous_subjects(self) -> list[str]:
        return [sub for s in self.items for sub in s.anonymous_subjects()]

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


__all__ = [
    "Service",
    "Message",
    "Services",
    "Subscriber",
    "SubjectScope",
    "SubscriberCallback",
    "subject_scope",
    "is_scoped_subject",
    "rescope",
]
