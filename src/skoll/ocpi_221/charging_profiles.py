from attrs import define, field
from skoll.domain import Enum, Object

from .base import URL, CiStr, Date, Number


class ChargingRateUnitType(Enum):

    W = "W"
    A = "A"


class ChargingProfileResponseType(Enum):

    ACCEPTED = "ACCEPTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    REJECTED = "REJECTED"
    TOO_OFTEN = "TOO_OFTEN"
    UNKNOWN_SESSION = "UNKNOWN_SESSION"


class ChargingProfileResultType(Enum):

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


@define(kw_only=True, frozen=True, slots=True)
class ChargingProfilePeriod(Object):

    limit: Number
    start_period: int
    number_phases: int | None = None


@define(kw_only=True, frozen=True, slots=True)
class ChargingProfile(Object):

    duration: int | None = None
    start_date_time: Date | None = None
    charging_rate_unit: ChargingRateUnitType
    min_charging_rate: Number | None = None
    charging_profile_period: list[ChargingProfilePeriod] = field(factory=list)


@define(kw_only=True, frozen=True, slots=True)
class SetChargingProfile(Object):

    response_url: URL
    charging_profile: ChargingProfile


@define(kw_only=True, frozen=True, slots=True)
class ActiveChargingProfile(Object):

    start_date_time: Date
    charging_profile: ChargingProfile


@define(kw_only=True, frozen=True, slots=True)
class ChargingProfileResponse(Object):

    result: ChargingProfileResponseType
    timeout: int


@define(kw_only=True, frozen=True, slots=True)
class ActiveChargingProfileResult(Object):

    result: ChargingProfileResultType
    profile: ActiveChargingProfile | None = None


@define(kw_only=True, frozen=True, slots=True)
class ChargingProfileResult(Object):

    result: ChargingProfileResultType


@define(kw_only=True, frozen=True, slots=True)
class ClearProfileResult(Object):

    result: ChargingProfileResultType


@define(kw_only=True, frozen=True, slots=True)
class GetChargingProfileParams(Object):

    duration: int
    response_url: URL
    session_id: CiStr[36]


@define(kw_only=True, frozen=True, slots=True)
class DeleteChargingProfile(Object):

    response_url: URL


@define(kw_only=True, frozen=True, slots=True)
class PutChargingProfileParams(Object):

    session_id: CiStr[36]
    data: SetChargingProfile


@define(kw_only=True, frozen=True, slots=True)
class DeleteChargingProfileParams(Object):

    response_url: URL
    session_id: CiStr[36]


@define(kw_only=True, frozen=True, slots=True)
class SIPutChargingProfileParams(Object):

    session_id: CiStr[36]
    data: ActiveChargingProfile


__all__ = [
    "ActiveChargingProfile",
    "ActiveChargingProfileResult",
    "ChargingProfileResponse",
    "ChargingProfileResponseType",
    "ChargingProfileResult",
    "ChargingProfileResultType",
    "ChargingProfile",
    "SetChargingProfile",
    "ChargingRateUnitType",
    "ChargingProfilePeriod",
    "ClearProfileResult",
    "DeleteChargingProfile",
    "GetChargingProfileParams",
    "PutChargingProfileParams",
    "DeleteChargingProfileParams",
    "SIPutChargingProfileParams",
]
