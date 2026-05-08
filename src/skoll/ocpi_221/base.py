import re
import typing as t
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from attrs import define, field

from skoll.result import ok, fail, Result
from skoll.domain import Enum, Object
from skoll.utils import to_tz, safe_call, to_snake_case
from skoll.exceptions import InvalidField


@define(kw_only=True, frozen=True, slots=True)
class CiStr(Object):

    value: str
    MAX_LENGTH: t.ClassVar[int] = 255
    REGEX: t.ClassVar[str] = r"^[ -~]*$"

    def __class_getitem__(cls, params: tuple[int, str] | int) -> type["CiStr"]:
        if isinstance(params, tuple):
            max_length, regex = params
        else:
            max_length, regex = params, r"^[ -~]*$"
        # print(max_length, regex)
        return type(f"CiStr{max_length}", (CiStr,), {"MAX_LENGTH": max_length, "REGEX": regex})

    @classmethod
    @t.override
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        if not isinstance(raw, str):
            raw = str(raw)

        value = raw.strip()

        print(value, cls.MAX_LENGTH, cls.REGEX, re.compile(cls.REGEX).match(value))

        if len(value) <= cls.MAX_LENGTH and re.compile(cls.REGEX).match(value):
            return ok(value)

        return fail(
            InvalidField(
                field=to_snake_case(cls.__name__),
                hints={"max_length": cls.MAX_LENGTH, "expected": "Printable ASCII only", "received": raw},
            )
        )


@define(kw_only=True, frozen=True, slots=True)
class Number(Object):

    value: float

    @classmethod
    @t.override
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        value = safe_call(float, raw)
        if value is not None and value >= 0:
            return ok(value)
        return fail(
            InvalidField(
                field=to_snake_case(cls.__name__),
                hints={"expected": "number", "received": raw},
            )
        )


@define(kw_only=True, frozen=True, slots=True)
class URL(Object):

    value: str

    @classmethod
    @t.override
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        value = str(raw).strip()
        try:
            result = urlparse(value)
            if all([result.scheme, result.netloc]) and len(value) <= 255:
                return ok(value)
        except Exception:
            pass

        return fail(InvalidField(field=to_snake_case(cls.__name__), hints={"expected": "Absolute URL (max 255 chars)"}))


@define(kw_only=True, slots=True, frozen=True)
class Price(Object):

    excl_vat: Number
    incl_vat: Number | None = None


@define(kw_only=True, slots=True, frozen=True)
class DisplayText(Object):

    text: CiStr[2]
    language: CiStr[512]


class Role(Enum):

    CPO = "CPO"
    HUB = "HUB"
    NAP = "NAP"
    NSP = "NSP"
    EMSP = "EMSP"
    SCSP = "SCSP"
    OTHER = "OTHER"


class ImageCategory(Enum):

    OWNER = "OWNER"
    OTHER = "OTHER"
    NETWORK = "NETWORK"
    CHARGER = "CHARGER"
    LOCATION = "LOCATION"
    ENTRANCE = "ENTRANCE"
    OPERATOR = "OPERATOR"


@define(kw_only=True, slots=True, frozen=True)
class Image(Object):

    url: str
    type: str
    category: ImageCategory
    width: int | None = None
    height: int | None = None
    thumbnail: str | None = None


@define(kw_only=True, slots=True, frozen=True)
class BusinessDetails(Object):

    name: str
    logo: Image | None = None
    website: URL | None = None


@define(kw_only=True, frozen=True, slots=True)
class GeoLocation(Object):

    latitude: CiStr[255, r"-?[0-9]{1,2}\.[0-9]{5,7}"]
    longitude: CiStr[255, r"-?[0-9]{1,3}\.[0-9]{5,7}"]


@define(kw_only=True, slots=True, frozen=True)
class AdditionalGeoLocation(Object):

    name: DisplayText | None = None
    latitude: CiStr[255, r"-?[0-9]{1,2}\.[0-9]{5,7}"]
    longitude: CiStr[255, r"-?[0-9]{1,3}\.[0-9]{5,7}"]


@define(kw_only=True, slots=True, frozen=True)
class Date(Object):

    value: datetime

    @t.override
    def serialize(self):

        if self.value.microsecond == 0:
            return self.value.strftime("%Y-%m-%dT%H:%M:%SZ")
        return self.value.strftime("%Y-%m-%dT%H:%M:%S.%f").rstrip("0").rstrip(".") + "Z"

    def diff(self, other: t.Self) -> timedelta:
        if other.value > self.value:
            return other.value - self.value
        return self.value - other.value

    def plus(
        self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0, delta: timedelta | None = None
    ) -> t.Self:
        new_date = (
            self.value + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds) + (delta or timedelta())
        )
        return self.__class__(value=new_date)

    def minus(
        self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0, delta: timedelta | None = None
    ) -> t.Self:
        new_date = (
            self.value - timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds) - (delta or timedelta())
        )
        return self.__class__(value=new_date)

    def __gt__(self, other: t.Self) -> bool:
        return self.value > other.value

    def __lt__(self, other: t.Self) -> bool:
        return self.value < other.value

    def __ge__(self, other: t.Self) -> bool:
        return self.value >= other.value

    def __le__(self, other: t.Self) -> bool:
        return self.value <= other.value

    @classmethod
    def today(cls, tz: str = "UTC") -> t.Self:
        return cls.now(tz=tz).reset(hour=0, minute=0, second=0)

    @classmethod
    def tomorrow(cls, tz_str: str = "UTC") -> t.Self:
        return cls.today(tz=tz_str).plus(days=1)

    @classmethod
    def now(cls, tz: str = "UTC") -> t.Self:
        return cls(value=datetime.now(tz=to_tz(tz)))

    def reset(
        self, day: int | None = None, hour: int | None = None, minute: int | None = None, second: int | None = None
    ) -> t.Self:
        date = self.value.replace(
            microsecond=0,
            tzinfo=self.value.tzinfo,
            day=day if day is not None else self.value.day,
            hour=hour if hour is not None else self.value.hour,
            minute=minute if minute is not None else self.value.minute,
            second=second if second is not None else self.value.second,
        )
        return self.__class__(value=date)

    @t.override
    @classmethod
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        if isinstance(raw, int):
            raw = datetime.fromtimestamp(raw / 1000, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw = str(raw).strip()
        if "T" in raw and not raw.endswith("Z") and "+" not in raw:
            raw = raw + "Z"
        ISO_8601_REGEX = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
        value = safe_call(lambda: datetime.fromisoformat(raw).replace(tzinfo=UTC))

        if value and re.match(ISO_8601_REGEX, raw):
            return ok(value)

        return fail(
            InvalidField(field=to_snake_case(cls.__name__), hints={"expected": "OCPI DateTime format", "received": raw})
        )


class EnergySourceCategory(Enum):

    GAS = "GAS"
    COAL = "COAL"
    WIND = "WIND"
    SOLAR = "SOLAR"
    WATER = "WATER"
    NUCLEAR = "NUCLEAR"
    GENERAL_GREEN = "GENERAL_GREEN"
    GENERAL_FOSSIL = "GENERAL_FOSSIL"


class EnvironmentalImpactCategory(Enum):

    NUCLEAR_WASTE = "NUCLEAR_WASTE"
    CARBON_DIOXIDE = "CARBON_DIOXIDE"


@define(kw_only=True, frozen=True, slots=True)
class EnergySource(Object):

    percentage: Number
    source: EnergySourceCategory


@define(kw_only=True, frozen=True, slots=True)
class EnvironmentalImpact(Object):

    amount: Number
    category: EnvironmentalImpactCategory


@define(kw_only=True, frozen=True, slots=True)
class EnergyMix(Object):

    is_green_energy: bool
    supplier_name: str | None = None
    environ_impact: list[EnvironmentalImpact] = field(factory=list)
    energy_product_name: str | None = None
    energy_sources: list[EnergySource] = field(factory=list)


@define(kw_only=True, frozen=True, slots=True)
class PartialEnergyMix(Object):

    is_green_energy: bool | None = None
    supplier_name: str | None = None
    environ_impact: list[EnvironmentalImpact] | None = None
    energy_product_name: str | None = None
    energy_sources: list[EnergySource] | None = None


Currency = CiStr[3, r"^[A-Z]{3}$"]
PartyID = CiStr[3, r"^[A-Z0-9]{3}$"]
CountryCode = CiStr[2, r"^[A-Z]{2}$"]


__all__ = [
    "URL",
    "Date",
    "Role",
    "CiStr",
    "Image",
    "Price",
    "Number",
    "PartyID",
    "Currency",
    "EnergyMix",
    "GeoLocation",
    "DisplayText",
    "CountryCode",
    "EnergySource",
    "ImageCategory",
    "BusinessDetails",
    "PartialEnergyMix",
    "EnvironmentalImpact",
    "EnergySourceCategory",
    "AdditionalGeoLocation",
    "EnvironmentalImpactCategory",
]
