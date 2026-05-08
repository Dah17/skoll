from attrs import define, field

from skoll.domain import Enum, Object

from .base import Date, Price, Number, PartyID, Currency, CountryCode
from .cdrs import CdrToken, ChargingPeriod
from .tokens import AuthMethod


class SessionStatus(Enum):

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    INVALID = "INVALID"
    PENDING = "PENDING"
    RESERVATION = "RESERVATION"


@define(kw_only=True, frozen=True, slots=True)
class Session(Object):

    country_code: CountryCode
    party_id: PartyID
    id: str
    start_date_time: Date
    end_date_time: Date | None = None
    kwh: Number
    cdr_token: CdrToken
    auth_method: AuthMethod
    location_id: str
    evse_uid: str
    connector_id: str | None = None
    meter_id: str | None = None
    currency: Currency
    charging_periods: list[ChargingPeriod] = field(factory=list)
    total_cost: Price | None = None
    status: SessionStatus
    last_updated: Date


@define(kw_only=True, frozen=True, slots=True)
class PartialSession(Object):

    country_code: CountryCode | None = None
    party_id: PartyID | None = None
    id: str | None = None
    start_date_time: Date | None = None
    end_date_time: Date | None = None
    kwh: Number | None = None
    cdr_token: CdrToken | None = None
    auth_method: AuthMethod | None = None
    location_id: str | None = None
    evse_uid: str | None = None
    connector_id: str | None = None
    meter_id: str | None = None
    currency: Currency | None = None
    charging_periods: list[ChargingPeriod] | None = None
    total_cost: Price | None = None
    status: SessionStatus | None = None
    last_updated: Date | None = None


@define(kw_only=True, frozen=True, slots=True)
class ListSessionsParams(Object):

    date_from: Date | None = None
    date_to: Date | None = None
    offset: int | None = None
    limit: int | None = None


@define(kw_only=True, frozen=True, slots=True)
class GetSessionParams(Object):

    party_id: PartyID
    country_code: CountryCode
    session_id: str


__all__ = ["Session", "SessionStatus", "PartialSession", "GetSessionParams", "ListSessionsParams"]
