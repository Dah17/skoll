from attrs import define, field

from skoll.domain import Enum, Object

from .base import (
    URL,
    Date,
    CiStr,
    Image,
    PartyID,
    GeoLocation,
    DisplayText,
    EnergyMix,
    CountryCode,
    BusinessDetails,
    PartialEnergyMix,
    AdditionalGeoLocation,
)


class Capability(Enum):

    CHARGING_PROFILE_CAPABLE = "CHARGING_PROFILE_CAPABLE"
    CHARGING_PREFERENCES_CAPABLE = "CHARGING_PREFERENCES_CAPABLE"
    CHIP_CARD_SUPPORT = "CHIP_CARD_SUPPORT"
    CONTACTLESS_CARD_SUPPORT = "CONTACTLESS_CARD_SUPPORT"
    CREDIT_CARD_PAYABLE = "CREDIT_CARD_PAYABLE"
    DEBIT_CARD_PAYABLE = "DEBIT_CARD_PAYABLE"
    PED_TERMINAL = "PED_TERMINAL"
    REMOTE_START_STOP_CAPABLE = "REMOTE_START_STOP_CAPABLE"
    RESERVABLE = "RESERVABLE"
    RFID_READER = "RFID_READER"
    START_SESSION_CONNECTOR_REQUIRED = "START_SESSION_CONNECTOR_REQUIRED"
    TOKEN_GROUP_CAPABLE = "TOKEN_GROUP_CAPABLE"
    UNLOCK_CAPABLE = "UNLOCK_CAPABLE"


class ConnectorType(Enum):

    CHADEMO = "CHADEMO"
    CHAOJI = "CHAOJI"
    DOMESTIC_A = "DOMESTIC_A"
    DOMESTIC_B = "DOMESTIC_B"
    DOMESTIC_C = "DOMESTIC_C"
    DOMESTIC_D = "DOMESTIC_D"
    DOMESTIC_E = "DOMESTIC_E"
    DOMESTIC_F = "DOMESTIC_F"
    DOMESTIC_G = "DOMESTIC_G"
    DOMESTIC_H = "DOMESTIC_H"
    DOMESTIC_I = "DOMESTIC_I"
    DOMESTIC_J = "DOMESTIC_J"
    DOMESTIC_K = "DOMESTIC_K"
    DOMESTIC_L = "DOMESTIC_L"
    IEC_60309_2_SINGLE_16 = "IEC_60309_2_SINGLE_16"
    IEC_60309_2_THREE_16 = "IEC_60309_2_THREE_16"
    IEC_60309_2_THREE_32 = "IEC_60309_2_THREE_32"
    IEC_60309_2_THREE_64 = "IEC_60309_2_THREE_64"
    IEC_62196_T1 = "IEC_62196_T1"
    IEC_62196_T1_COMBO = "IEC_62196_T1_COMBO"
    IEC_62196_T2 = "IEC_62196_T2"
    IEC_62196_T2_COMBO = "IEC_62196_T2_COMBO"
    IEC_62196_T3A = "IEC_62196_T3A"
    IEC_62196_T3C = "IEC_62196_T3C"
    NEMA_5_20 = "NEMA_5_20"
    NEMA_6_30 = "NEMA_6_30"
    NEMA_6_50 = "NEMA_6_50"
    NEMA_10_30 = "NEMA_10_30"
    NEMA_10_50 = "NEMA_10_50"
    NEMA_14_30 = "NEMA_14_30"
    NEMA_14_50 = "NEMA_14_50"
    PANTOGRAPH_BOTTOM_UP = "PANTOGRAPH_BOTTOM_UP"
    PANTOGRAPH_TOP_DOWN = "PANTOGRAPH_TOP_DOWN"
    TESLA_R = "TESLA_R"
    TESLA_S = "TESLA_S"


class ConnectorFormat(Enum):

    SOCKET = "SOCKET"
    CABLE = "CABLE"


class PowerType(Enum):

    AC_1_PHASE = "AC_1_PHASE"
    AC_3_PHASE = "AC_3_PHASE"
    DC = "DC"


class ParkingType(Enum):

    ALONG_MOTORWAY = "ALONG_MOTORWAY"
    PARKING_GARAGE = "PARKING_GARAGE"
    PARKING_LOT = "PARKING_LOT"
    ON_DRIVEWAY = "ON_DRIVEWAY"
    ON_STREET = "ON_STREET"
    UNDERGROUND_GARAGE = "UNDERGROUND_GARAGE"


class Facility(Enum):

    HOTEL = "HOTEL"
    RESTAURANT = "RESTAURANT"
    CAFE = "CAFE"
    MALL = "MALL"
    SUPERMARKET = "SUPERMARKET"
    SPORT = "SPORT"
    RECREATION_AREA = "RECREATION_AREA"
    NATURE = "NATURE"
    MUSEUM = "MUSEUM"
    BIKE_SHARING = "BIKE_SHARING"
    BUS_STOP = "BUS_STOP"
    TAXI_STAND = "TAXI_STAND"
    TRAIN_STATION = "TRAIN_STATION"
    AIRPORT = "AIRPORT"
    CARPOOL_PARKING = "CARPOOL_PARKING"
    FUEL_STATION = "FUEL_STATION"
    WIFI = "WIFI"


class LocationType(Enum):

    ON_STREET = "ON_STREET"
    PARKING_GARAGE = "PARKING_GARAGE"
    UNDERGROUND_GARAGE = "UNDERGROUND_GARAGE"
    PARKING_LOT = "PARKING_LOT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class EvseStatus(Enum):

    AVAILABLE = "AVAILABLE"
    BLOCKED = "BLOCKED"
    CHARGING = "CHARGING"
    INOPERATIVE = "INOPERATIVE"
    OUTOFORDER = "OUTOFORDER"
    PLANNED = "PLANNED"
    REMOVED = "REMOVED"
    RESERVED = "RESERVED"
    UNKNOWN = "UNKNOWN"


@define(kw_only=True, frozen=True, slots=True)
class RegularHours(Object):

    weekday: int
    period_begin: CiStr[5, r"^([01]\\d|2[0-3]):[0-5]\\d$"]
    period_end: CiStr[5, r"^([01]\\d|2[0-3]):[0-5]\\d$"]


@define(kw_only=True, frozen=True, slots=True)
class ExceptionalPeriod(Object):

    period_begin: Date
    period_end: Date


@define(kw_only=True, frozen=True, slots=True)
class Hours(Object):

    twentyfourseven: bool
    regular_hours: list[RegularHours] = field(factory=list)
    exceptional_openings: list[ExceptionalPeriod] = field(factory=list)
    exceptional_closings: list[ExceptionalPeriod] = field(factory=list)


@define(kw_only=True, frozen=True, slots=True)
class Connector(Object):

    id: str
    standard: ConnectorType
    format: ConnectorFormat
    power_type: PowerType
    max_voltage: int
    max_amperage: int
    max_electric_power: int | None = None
    tariff_ids: list[str] = field(factory=list)
    terms_and_conditions: URL | None = None
    last_updated: Date


@define(kw_only=True, frozen=True, slots=True)
class PartialConnector(Object):

    id: str | None = None
    standard: ConnectorType | None = None
    format: ConnectorFormat | None = None
    power_type: PowerType | None = None
    max_voltage: int | None = None
    max_amperage: int | None = None
    max_electric_power: int | None = None
    tariff_ids: list[str] | None = None
    terms_and_conditions: URL | None = None
    last_updated: Date | None = None


@define(kw_only=True, frozen=True, slots=True)
class EVSE(Object):

    uid: str
    evse_id: str | None = None
    status: EvseStatus
    capabilities: list[Capability] = field(factory=list)
    connectors: list[Connector] = field(factory=list)
    floor_level: str | None = None
    coordinates: GeoLocation | None = None
    physical_reference: str | None = None
    directions: list[DisplayText] = field(factory=list)
    parking_restrictions: list[str] = field(factory=list)
    images: list[Image] = field(factory=list)
    last_updated: Date


@define(kw_only=True, frozen=True, slots=True)
class PartialEVSE(Object):

    uid: str | None = None
    evse_id: str | None = None
    status: EvseStatus | None = None
    capabilities: list[Capability] | None = None
    connectors: list[PartialConnector] | None = None
    floor_level: str | None = None
    coordinates: GeoLocation | None = None
    physical_reference: str | None = None
    directions: list[DisplayText] | None = None
    parking_restrictions: list[str] | None = None
    images: list[Image] | None = None
    last_updated: Date | None = None


@define(kw_only=True, frozen=True, slots=True)
class Location(Object):

    id: str
    type: LocationType
    name: str | None = None
    address: str
    city: str
    postal_code: str | None = None
    state: str | None = None
    country: CountryCode
    coordinates: GeoLocation
    related_locations: list[AdditionalGeoLocation] = field(factory=list)
    parking_type: ParkingType | None = None
    evses: list[EVSE] = field(factory=list)
    directions: list[DisplayText] = field(factory=list)
    operator: BusinessDetails | None = None
    suboperator: BusinessDetails | None = None
    owner: BusinessDetails | None = None
    facilities: list[Facility] = field(factory=list)
    time_zone: str
    opening_times: Hours | None = None
    charging_when_closed: bool | None = None
    images: list[Image] = field(factory=list)
    energy_mix: EnergyMix | None = None
    last_updated: Date


@define(kw_only=True, frozen=True, slots=True)
class PartialLocation(Object):

    id: str | None = None
    type: LocationType | None = None
    name: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    state: str | None = None
    country: CountryCode | None = None
    coordinates: GeoLocation | None = None
    related_locations: list[AdditionalGeoLocation] | None = None
    parking_type: ParkingType | None = None
    evses: list[PartialEVSE] | None = None
    directions: list[DisplayText] | None = None
    operator: BusinessDetails | None = None
    suboperator: BusinessDetails | None = None
    owner: BusinessDetails | None = None
    facilities: list[Facility] | None = None
    time_zone: str | None = None
    opening_times: Hours | None = None
    charging_when_closed: bool | None = None
    images: list[Image] | None = None
    energy_mix: PartialEnergyMix | None = None
    last_updated: Date | None = None


@define(kw_only=True, frozen=True, slots=True)
class ListLocationsParams(Object):

    limit: int | None = None
    offset: int | None = None
    date_to: Date | None = None
    date_from: Date | None = None


@define(kw_only=True, frozen=True, slots=True)
class GetLocationParams(Object):

    location_id: str
    party_id: PartyID
    country_code: CountryCode


@define(kw_only=True, frozen=True, slots=True)
class GetEvseParams(Object):

    evse_uid: str
    location_id: str
    party_id: PartyID
    country_code: CountryCode


@define(kw_only=True, frozen=True, slots=True)
class GetConnectorParams(Object):

    evse_uid: str
    location_id: str
    connector_id: str
    party_id: PartyID
    country_code: CountryCode


__all__ = [
    "EVSE",
    "Hours",
    "Facility",
    "Location",
    "PowerType",
    "EvseStatus",
    "Connector",
    "Capability",
    "PartialEVSE",
    "ParkingType",
    "LocationType",
    "RegularHours",
    "ConnectorType",
    "GetEvseParams",
    "PartialLocation",
    "ConnectorFormat",
    "PartialConnector",
    "GetLocationParams",
    "ExceptionalPeriod",
    "GetConnectorParams",
    "ListLocationsParams",
]
