from __future__ import annotations

import typing as t
from datetime import timedelta
from attrs import define, field

from skoll.domain.base import Object
from skoll.domain.primitives import ID, PositiveInt, DateTime, Latitude, Longitude, Time, LocalizedText


__all__ = [
    "Period",
    "Address",
    "Message",
    "TimeSlot",
    "Coordinate",
    "EntityState",
    "RegularHours",
    "SpecialHours",
    "WorkingHours",
    "MessageContext",
    "MessagePayload",
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
class EntityState(Object):

    id: ID = field(factory=ID.new)
    created_at: DateTime = field(factory=DateTime.now)
    updated_at: DateTime = field(factory=DateTime.now)
    version: PositiveInt = field(factory=PositiveInt.zero)

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

    @t.override
    def evolve(self, **kwargs: t.Any) -> t.Self:
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = DateTime.now()
        if "version" not in kwargs:
            kwargs["version"] = self.version.increment()
        return super().evolve(**kwargs)


@define(frozen=True, kw_only=True, slots=True)
class MessageContext(Object):

    span_id: ID = field(factory=ID.new)
    trace_id: ID = field(factory=ID.new)

    @classmethod
    def default(cls) -> t.Self:
        return cls()


@define(frozen=True, kw_only=True, slots=True)
class MessagePayload(Object):

    @classmethod
    def default(cls) -> t.Self:
        return cls()


@define(frozen=True, kw_only=True, slots=True, eq=False)
class Message(Object):

    topic: str
    source: str
    id: ID = field(factory=ID.new)
    created_at: DateTime = field(factory=DateTime.now)
    payload: MessagePayload = field(factory=MessagePayload.default)
    context: MessageContext = field(factory=MessageContext.default)

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
