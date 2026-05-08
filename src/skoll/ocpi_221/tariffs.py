from attrs import define, field

from skoll.domain import Enum, Object

from .base import URL, Date, Price, Number, PartyID, Currency, EnergyMix, DisplayText, CountryCode, PartialEnergyMix


class TariffDimensionType(Enum):

    ENERGY = "ENERGY"
    FLAT = "FLAT"
    PARKING_TIME = "PARKING_TIME"
    TIME = "TIME"


class TariffType(Enum):

    AD_HOC_PAYMENT = "AD_HOC_PAYMENT"
    PROFILE_CHEAP = "PROFILE_CHEAP"
    PROFILE_FAST = "PROFILE_FAST"
    PROFILE_GREEN = "PROFILE_GREEN"
    REGULAR = "REGULAR"


@define(kw_only=True, frozen=True, slots=True)
class TariffRestrictions(Object):

    start_time: str | None = None
    end_time: str | None = None
    start_date: Date | None = None
    end_date: Date | None = None
    min_kwh: Number | None = None
    max_kwh: Number | None = None
    min_power: Number | None = None
    max_power: Number | None = None
    min_duration: int | None = None
    max_duration: int | None = None
    day_of_week: list[str] = field(factory=list)
    reservation: bool | None = None


@define(kw_only=True, frozen=True, slots=True)
class PriceComponent(Object):

    type: TariffDimensionType
    price: Number
    vat: Number | None = None
    step_size: int


@define(kw_only=True, frozen=True, slots=True)
class TariffElement(Object):

    price_components: list[PriceComponent] = field(factory=list)
    restrictions: TariffRestrictions | None = None


@define(kw_only=True, frozen=True, slots=True)
class Tariff(Object):

    country_code: CountryCode
    party_id: PartyID
    id: str
    currency: Currency
    type: TariffType | None = None
    tariff_alt_text: list[DisplayText] = field(factory=list)
    tariff_alt_url: URL | None = None
    min_price: Price | None = None
    max_price: Price | None = None
    elements: list[TariffElement] = field(factory=list)
    start_date_time: Date | None = None
    end_date_time: Date | None = None
    energy_mix: EnergyMix | None = None
    last_updated: Date


@define(kw_only=True, frozen=True, slots=True)
class PartialTariff(Object):

    country_code: CountryCode | None = None
    party_id: PartyID | None = None
    id: str | None = None
    currency: Currency | None = None
    type: TariffType | None = None
    tariff_alt_text: list[DisplayText] | None = None
    tariff_alt_url: URL | None = None
    min_price: Price | None = None
    max_price: Price | None = None
    elements: list[TariffElement] | None = None
    start_date_time: Date | None = None
    end_date_time: Date | None = None
    energy_mix: PartialEnergyMix | None = None
    last_updated: Date | None = None


@define(kw_only=True, frozen=True, slots=True)
class ListTariffsParams(Object):

    limit: int | None = None
    offset: int | None = None
    date_to: Date | None = None
    date_from: Date | None = None


@define(kw_only=True, frozen=True, slots=True)
class GetTariffParams(Object):

    tariff_id: str
    party_id: PartyID
    country_code: CountryCode


__all__ = [
    "Tariff",
    "TariffType",
    "TariffElement",
    "PartialTariff",
    "PriceComponent",
    "GetTariffParams",
    "ListTariffsParams",
    "TariffRestrictions",
    "TariffDimensionType",
]
