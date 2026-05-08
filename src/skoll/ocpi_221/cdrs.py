from attrs import define, field
from skoll.domain import Enum, Object

from .tariffs import Tariff
from .tokens import AuthMethod
from .locations import ConnectorType, ConnectorFormat, PowerType
from .base import URL, Date, Price, Number, PartyID, Currency, GeoLocation, CountryCode


class CdrTokenType(Enum):

    RFID = "RFID"
    OTHER = "OTHER"
    APP_USER = "APP_USER"
    AD_HOC_USER = "AD_HOC_USER"


class CdrDimensionType(Enum):

    TIME = "TIME"
    POWER = "POWER"
    ENERGY = "ENERGY"
    CURRENT = "CURRENT"
    MAX_POWER = "MAX_POWER"
    MIN_POWER = "MIN_POWER"
    MAX_CURRENT = "MAX_CURRENT"
    MIN_CURRENT = "MIN_CURRENT"
    PARKING_TIME = "PARKING_TIME"
    ENERGY_EXPORT = "ENERGY_EXPORT"
    ENERGY_IMPORT = "ENERGY_IMPORT"
    STATE_OF_CHARGE = "STATE_OF_CHARGE"
    RESERVATION_TIME = "RESERVATION_TIME"


@define(kw_only=True, frozen=True, slots=True)
class CdrToken(Object):

    uid: str
    contract_id: str
    type: CdrTokenType


@define(kw_only=True, frozen=True, slots=True)
class CdrDimension(Object):

    volume: Number
    type: CdrDimensionType


@define(kw_only=True, frozen=True, slots=True)
class ChargingPeriod(Object):

    start_date_time: Date
    tariff_id: str | None = None
    dimensions: list[CdrDimension] = field(factory=list)


@define(kw_only=True, frozen=True, slots=True)
class CdrLocation(Object):

    id: str
    name: str | None = None
    address: str
    city: str
    postal_code: str | None = None
    country: CountryCode
    coordinates: GeoLocation
    evse_uid: str
    evse_id: str | None = None
    connector_id: str | None = None
    connector_standard: ConnectorType | None = None
    connector_format: ConnectorFormat | None = None
    connector_power_type: PowerType | None = None


@define(kw_only=True, frozen=True, slots=True)
class SignedValue(Object):

    nature: str
    plain_data: str
    signed_data: str


@define(kw_only=True, frozen=True, slots=True)
class SignedData(Object):

    encoding_method: str
    public_key: str
    signed_values: list[SignedValue] = field(factory=list)
    url: URL | None = None


@define(kw_only=True, frozen=True, slots=True)
class Cdr(Object):

    country_code: CountryCode
    party_id: PartyID
    id: str
    start_date_time: Date
    end_date_time: Date
    session_id: str | None = None
    cdr_token: CdrToken
    auth_method: AuthMethod
    cdr_location: CdrLocation
    currency: Currency
    tariffs: list[Tariff] = field(factory=list)
    charging_periods: list[ChargingPeriod] = field(factory=list)
    signed_data: SignedData | None = None
    total_cost: Price
    total_fixed_cost: Price | None = None
    total_energy: Number
    total_energy_cost: Price | None = None
    total_time: Number
    total_time_cost: Price | None = None
    total_parking_time: Number | None = None
    total_parking_cost: Price | None = None
    total_reservation_cost: Price | None = None
    remark: str | None = None
    invoice_reference_id: str | None = None
    credit: bool | None = None
    credit_reference_id: str | None = None
    home_charging_compensation: bool | None = None
    last_updated: Date


@define(kw_only=True, frozen=True, slots=True)
class PartialCdr(Object):

    country_code: CountryCode | None = None
    party_id: PartyID | None = None
    id: str | None = None
    start_date_time: Date | None = None
    end_date_time: Date | None = None
    session_id: str | None = None
    cdr_token: CdrToken | None = None
    auth_method: AuthMethod | None = None
    cdr_location: CdrLocation | None = None
    currency: Currency | None = None
    tariffs: list[Tariff] | None = None
    charging_periods: list[ChargingPeriod] | None = None
    signed_data: SignedData | None = None
    total_cost: Price | None = None
    total_fixed_cost: Price | None = None
    total_energy: Number | None = None
    total_energy_cost: Price | None = None
    total_time: Number | None = None
    total_time_cost: Price | None = None
    total_parking_time: Number | None = None
    total_parking_cost: Price | None = None
    total_reservation_cost: Price | None = None
    remark: str | None = None
    invoice_reference_id: str | None = None
    credit: bool | None = None
    credit_reference_id: str | None = None
    home_charging_compensation: bool | None = None
    last_updated: Date | None = None


@define(kw_only=True, frozen=True, slots=True)
class ListCdrsParams(Object):

    limit: int | None = None
    offset: int | None = None
    date_to: Date | None = None
    date_from: Date | None = None


@define(kw_only=True, frozen=True, slots=True)
class GetCdrParams(Object):

    cdr_id: str
    party_id: PartyID | None = None
    country_code: CountryCode | None = None


__all__ = [
    "Cdr",
    "CdrToken",
    "SignedData",
    "PartialCdr",
    "CdrLocation",
    "SignedValue",
    "CdrDimension",
    "GetCdrParams",
    "CdrTokenType",
    "ListCdrsParams",
    "ChargingPeriod",
    "CdrDimensionType",
]
