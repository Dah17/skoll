import typing as t

from datetime import timedelta
from attrs import define, field
from abc import abstractmethod, ABC
from skoll.utils import create_db_cursor

from .primitives import *

__all__ = [
    "Entity",
    "Period",
    "Address",
    "TimeSlot",
    "Coordinate",
    "CursorPage",
    "RegularHours",
    "SpecialHours",
    "WorkingHours",
]


@define(kw_only=True, slots=True, frozen=True)
class Coordinate(Object):

    lat: Latitude
    lng: Longitude

    @classmethod
    def from_raw(cls, lat: float, lng: float):
        return Coordinate(lat=Latitude(value=lat), lng=Longitude(value=lng))


@define(kw_only=True, slots=True, frozen=True)
class Address(Object):

    city: str
    street: str
    region: str
    country: str
    postal_code: str
    coordinate: Coordinate


@define(kw_only=True, slots=True, frozen=True)
class Period(Object):

    end: DateTime
    start: DateTime

    @property
    def duration(self) -> timedelta:
        return self.end.diff(self.start)

    def days(self, tz_str: str = "UTC") -> list[DateTime]:
        dates: list[DateTime] = []
        date = self.start.to_tz(tz_str=tz_str).reset_part(hour=True, minute=True).reset_second()
        while date < self.end.to_tz(tz_str=tz_str):
            dates.append(date)
            date = date.plus(days=1)

        return dates


@define(kw_only=True, slots=True, frozen=True)
class TimeSlot(Object):

    end: Time
    start: Time

    def is_between(self, hour: int, minute: int):
        hours = hour + (minute / 60)
        return self.start.as_hour <= hours and hours <= self.end.as_hour


@define(kw_only=True, slots=True, frozen=True)
class RegularHours(Object):

    weekday: list[int] = field(factory=list)
    slots: list[TimeSlot] = field(factory=list)


@define(kw_only=True, slots=True, frozen=True)
class SpecialHours(Object):

    opened: bool
    date: DateTime
    name: LocalizedText
    slots: list[TimeSlot] = field(factory=list)


@define(kw_only=True, slots=True, frozen=True)
class WorkingHours(Object):

    timezone: str
    always_open: bool
    regular_hours: list[RegularHours] = field(factory=list)
    special_hours: list[SpecialHours] = field(factory=list)


@define(kw_only=True, slots=True, frozen=True, eq=False)
class Entity[T: ID = Ulid](Object, ABC):
    """An identified aggregate that remembers the version storage last agreed with it on.

    `version` is the number written alongside the row, and every `evolve` moves it one step
    forward. `stored_version` is where storage was left: `None` while the aggregate has never been
    written, otherwise the version the row still carries. A repository reads both -- `None` means
    insert, a number is what the row must still show for an update to be safe -- which is what
    lets an aggregate be evolved as many times as the work needs before it is saved.

    It is internal: in-memory bookkeeping about persistence rather than part of the entity, so it
    is left out of `serialize` and of the creation schema, and a restored entity starts out looking
    unwritten. A repository closes that gap by calling `mark_stored` once the state and the row
    agree, on the way out of a read and after a successful write.
    """

    created_at: DateTime = field(factory=DateTime.now)
    updated_at: DateTime = field(factory=DateTime.now)
    version: PositiveInt = field(factory=PositiveInt.zero)

    stored_version: int | None = internal(default=None)

    @abstractmethod
    def get_id(self) -> T:
        raise NotImplementedError("Subclasses must implement the `id` property to return the correct ID type.")

    def mark_stored(self) -> None:
        """Record that storage now holds exactly this state, so later writes guard on this version.

        This writes through the frozen shell on purpose. What it sets is not part of the entity --
        not its identity, not its value, not what it serializes to -- it is a note about the row
        behind it, and handing back a copy would oblige every caller of `save` and every read path
        to rebind a variable to keep a fact they never asked to carry.
        """
        object.__setattr__(self, "stored_version", self.version.value)

    @t.override
    def __eq__(self, other: t.Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return other.get_id() == self.get_id()

    @t.override
    def __ne__(self, other: t.Any) -> bool:
        return not self == other

    @t.override
    def __hash__(self) -> int:
        return hash(self.get_id().value)

    @t.override
    def evolve(self, *, allow_none: bool = False, now: DateTime | None = None, **kwargs: t.Any) -> t.Self:
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = now or DateTime.now()
        if "version" not in kwargs:
            kwargs["version"] = self.version.increment()
        return super().evolve(allow_none=allow_none, **kwargs)


@define(kw_only=True, slots=True, frozen=True)
class CursorPage[T](Object):

    limit: int
    has_next: bool
    total_count: int
    next_cursor: str | None = None
    items: list[T] = field(factory=list)

    @classmethod
    def new[U](
        cls, *, items: list[U], total_count: int, limit: int, get_item_key: t.Callable[[U], str]
    ) -> "CursorPage[U]":
        has_next = len(items) == limit + 1
        page_items = items[:limit] if has_next else items

        next_cursor = create_db_cursor(get_item_key(items[-1]), total_count, limit) if has_next and page_items else None

        return CursorPage(
            limit=limit,
            items=page_items,
            has_next=has_next,
            total_count=total_count,
            next_cursor=next_cursor,
        )
