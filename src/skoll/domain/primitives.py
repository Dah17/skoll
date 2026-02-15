from __future__ import annotations

import re
import typing as t
from attrs import define, field
from datetime import datetime, timedelta, UTC

from skoll.errors import InvalidField
from skoll.domain.base import Object
from skoll.result import Result, ok, fail
from skoll.utils import new_ulid, to_tz, to_snake_case, safe_call

ID_REGEX = r"^[0-9a-z]{26}$"
EMAIL_REGEX = r"^[^@]+@[^@]+$"
TIME_REGEX = r"^(?:[01]?[0-9]|2[0-3]):[0-5][0-9]$"
LOCALE_PATTERN = r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2}|-[0-9]{3})?$"

__all__ = ["ID", "Time", "Email", "PositiveInt", "DateTime", "Latitude", "Longitude", "Locale", "LocalizedText"]


@define(kw_only=True, slots=True, frozen=True)
class ID(Object):

    value: str

    @classmethod
    def new(cls) -> t.Self:
        return cls(value=new_ulid())

    @t.override
    @classmethod
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        value = safe_call(str, raw)
        if value is not None and re.fullmatch(ID_REGEX, value.strip()) is not None:
            return ok(value.strip())
        return fail(
            InvalidField(
                field=to_snake_case(cls.__name__),
                hints={"expected": "string", "contraints": {"pattern": ID_REGEX}, "received": raw},
            )
        )


@define(kw_only=True, slots=True, frozen=True)
class PositiveInt(Object):

    value: int

    def increment(self) -> t.Self:
        return self.__class__(value=self.value + 1)

    def decrement(self) -> t.Self:
        return self.__class__(value=self.value - 1)

    @classmethod
    def zero(cls) -> t.Self:
        return cls(value=0)

    @t.override
    @classmethod
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        value = safe_call(int, raw)
        if value is not None and value >= 0:
            return ok(value)
        return fail(
            InvalidField(
                field=to_snake_case(cls.__name__),
                hints={"expected": "integer", "contraints": {"min": 0}, "received": raw},
            )
        )


@define(kw_only=True, slots=True, frozen=True)
class DateTime(Object):

    value: datetime

    @property
    def timestamp(self) -> int:
        return int(self.value.timestamp() * 1000)

    @property
    def week_day(self) -> int:
        return self.value.weekday()

    @property
    def iso_format(self) -> str:
        """ """
        return self.value.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

    @t.override
    def serialize(self):
        return self.timestamp

    def diff(self, other: t.Self) -> timedelta:
        if other.value > self.value:
            return other.value - self.value
        return self.value - other.value

    def plus(
        self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0, delta: timedelta | None = None
    ) -> DateTime:
        new_date = (
            self.value + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds) + (delta or timedelta())
        )
        return DateTime(value=new_date)

    def minus(
        self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0, delta: timedelta | None = None
    ) -> DateTime:
        new_date = (
            self.value - timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds) - (delta or timedelta())
        )
        return DateTime(value=new_date)

    def __gt__(self, other: t.Self) -> bool:
        return self.value > other.value

    def __lt__(self, other: t.Self) -> bool:
        return self.value < other.value

    def __ge__(self, other: t.Self) -> bool:
        return self.value >= other.value

    def __le__(self, other: t.Self) -> bool:
        return self.value <= other.value

    def reset_second(self):
        date = self.value.replace(second=0, microsecond=0)
        return DateTime(value=date)

    def reset_part(self, hour: bool = False, minute: bool = False):
        date = self.value.replace(second=0, microsecond=0)

        if hour:
            date = date.replace(hour=0, minute=0)
        elif minute:
            date = date.replace(minute=0)
        return DateTime(value=date)

    def to_tz(self, tz_str: str = "UTC") -> DateTime:
        return DateTime.from_timestamp(int(self.value.timestamp() * 1000), tz_str=tz_str)

    @classmethod
    def today(cls, tz_str: str = "UTC") -> DateTime:
        tz = to_tz(tz_str)
        value = datetime.combine(datetime.now(tz=tz), datetime.min.time()).replace(tzinfo=tz)
        return cls.from_timestamp(int(value.timestamp() * 1000), tz_str=tz_str)

    @classmethod
    def tomorrow(cls, tz_str: str = "UTC") -> DateTime:
        tz = to_tz(tz_str)
        value = datetime.combine(datetime.now(tz=tz) + timedelta(days=1), datetime.min.time()).replace(tzinfo=tz)
        return cls.from_timestamp(int(value.timestamp() * 1000), tz_str=tz_str)

    @classmethod
    def now(cls, tz_str: str = "UTC") -> DateTime:
        tz = to_tz(tz_str)
        value = int(datetime.now(tz=tz).timestamp() * 1000)
        return cls.from_timestamp(value, tz_str=tz_str)

    @classmethod
    def from_timestamp(cls, timestamp: int, tz_str: str = "UTC") -> DateTime:
        tz = to_tz(tz_str)
        return DateTime(value=datetime.fromtimestamp(timestamp / 1000, tz=tz))

    @t.override
    @classmethod
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        value = safe_call(int, raw)
        if value is not None and value >= 0:
            return ok(datetime.fromtimestamp(value / 1000, tz=UTC))
        return fail(
            InvalidField(
                field=to_snake_case(cls.__name__),
                hints={"expected": "integer", "contraints": {"min": 0}, "received": raw},
            )
        )


@define(kw_only=True, slots=True, frozen=True)
class Latitude(Object):
    value: float

    @t.override
    @classmethod
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        value = safe_call(float, raw)
        if value is not None and -90 <= value <= 90:
            return ok(value)
        return fail(
            InvalidField(
                field=to_snake_case(cls.__name__),
                hints={"expected": "float", "contraints": {"min": -90, "max": 90}, "received": raw},
            )
        )


@define(kw_only=True, slots=True, frozen=True)
class Longitude(Object):
    value: float

    @t.override
    @classmethod
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        value = safe_call(float, raw)
        if value is not None and -180 <= value <= 180:
            return ok(value)
        return fail(
            InvalidField(
                field=to_snake_case(cls.__name__),
                hints={"expected": "float", "contraints": {"min": -180, "max": 180}, "received": raw},
            )
        )


@define(kw_only=True, slots=True, frozen=True)
class Time(Object):
    value: str

    @property
    def as_hour(self) -> float:
        return self.hour + (self.minute / 60)

    @property
    def hour(self) -> int:
        return int(self.value.split(":")[0])

    @property
    def minute(self) -> int:
        return int(self.value.split(":")[1])

    @t.override
    @classmethod
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        value = safe_call(str, raw)
        if value is not None and re.fullmatch(TIME_REGEX, value.strip()) is not None:
            return ok(value.strip())

        return fail(
            InvalidField(
                field=to_snake_case(cls.__name__),
                hints={"expected": "string", "contraints": {"pattern": TIME_REGEX}, "received": raw},
            )
        )


@define(kw_only=True, slots=True, frozen=True)
class Email(Object):

    value: str

    @property
    def name(self) -> str:
        return self.value.split("@")[0]

    @classmethod
    def anonymous(cls, id: ID) -> Email:
        return cls(value=f"{id.value}.no-reply@email.com")

    @t.override
    @classmethod
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        value = safe_call(str, raw)
        if value is not None and re.fullmatch(EMAIL_REGEX, value.strip()) is not None:
            return ok(value.strip().lower())
        return fail(
            InvalidField(
                field=to_snake_case(cls.__name__),
                hints={"expected": "string", "contraints": {"pattern": EMAIL_REGEX}, "received": raw},
            )
        )


@define(kw_only=True, slots=True, frozen=True)
class Locale(Object):

    value: str

    @t.override
    @classmethod
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        value = safe_call(str, raw)
        if value is not None and re.fullmatch(LOCALE_PATTERN, value.strip()) is not None:
            return ok(value.strip().lower())
        return fail(
            InvalidField(
                field=to_snake_case(cls.__name__),
                hints={"received": raw, "expected": "BCP47Locale"},
            )
        )


@define(kw_only=True, slots=True, frozen=True)
class LocalizedText(Object):

    value: dict[str, str] = field(factory=dict)

    @t.override
    @classmethod
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        value = safe_call(dict, raw)

        if value is not None:
            keys_valid = all(isinstance(k, str) and re.fullmatch(LOCALE_PATTERN, k) for k in value.keys())
            values_valid = all(isinstance(v, str) for v in value.values())
            if keys_valid and values_valid:
                return ok(t.cast(dict[str, str], value))

        return fail(
            InvalidField(
                field=to_snake_case(cls.__name__),
                hints={
                    "received": raw,
                    "expected": "Dictionaire<BCP47Locale, string>",
                    "example": {"en-US": "English", "en": "An example"},
                },
            )
        )
