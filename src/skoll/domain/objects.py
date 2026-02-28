import typing as t

from datetime import timedelta
from attrs import define, field

from .primitives import (
    ID,
    Time,
    Object,
    DateTime,
    Latitude,
    Timezone,
    Currency,
    Longitude,
    PositiveInt,
    CountryCode,
    LocalizedText,
)


__all__ = [
    "Entity",
    "Period",
    "IPInfo",
    "Address",
    "TimeSlot",
    "Coordinate",
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
class IPInfo(Object):

    timezone: Timezone
    currency: Currency
    city: str | None = None
    country_code: CountryCode
    region_code: str | None = None


@define(kw_only=True, slots=True, frozen=True)
class WorkingHours(Object):

    timezone: str
    always_open: bool
    regular_hours: list[RegularHours] = field(factory=list)
    special_hours: list[SpecialHours] = field(factory=list)


@define(kw_only=True, slots=True, frozen=True, eq=False)
class Entity(Object):

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
    def evolve(self, allow_none: bool = False, **kwargs: t.Any) -> t.Self:
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = DateTime.now()
        if "version" not in kwargs:
            kwargs["version"] = self.version.increment()
        return super().evolve(allow_none=allow_none, **kwargs)
