from attrs import define, field

from skoll.domain import Enum, Object

from .base import URL, Date, DisplayText
from .tokens import Token


class CommandType(Enum):

    CANCEL_RESERVATION = "CANCEL_RESERVATION"
    RESERVE_NOW = "RESERVE_NOW"
    START_SESSION = "START_SESSION"
    STOP_SESSION = "STOP_SESSION"
    UNLOCK_CONNECTOR = "UNLOCK_CONNECTOR"


class CommandResponseType(Enum):

    NOT_SUPPORTED = "NOT_SUPPORTED"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    UNKNOWN_SESSION = "UNKNOWN_SESSION"
    UNKNOWN_TOKEN = "UNKNOWN_TOKEN"
    INVALID_PARAMETERS = "INVALID_PARAMETERS"


class CommandResultType(Enum):

    ACCEPTED = "ACCEPTED"
    CANCELED_RESERVATION = "CANCELED_RESERVATION"
    EVSE_INOPERATIVE = "EVSE_INOPERATIVE"
    EVSE_OCCUPIED = "EVSE_OCCUPIED"
    EVSE_UNKNOWN = "EVSE_UNKNOWN"
    FAILED = "FAILED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_LOCATION = "UNKNOWN_LOCATION"
    UNKNOWN_SESSION = "UNKNOWN_SESSION"
    UNKNOWN_TOKEN = "UNKNOWN_TOKEN"


@define(kw_only=True, frozen=True, slots=True)
class CommandResponse(Object):

    timeout: int | None = None
    result: CommandResponseType


@define(kw_only=True, frozen=True, slots=True)
class CommandResult(Object):

    result: CommandResultType
    message: list[DisplayText] = field(factory=list)


@define(kw_only=True, frozen=True, slots=True)
class StartSession(Object):

    response_url: URL
    token: Token
    location_id: str
    connector_id: str | None = None
    evse_uid: str | None = None
    authorization_reference: str | None = None


@define(kw_only=True, frozen=True, slots=True)
class StopSession(Object):

    response_url: URL
    session_id: str


@define(kw_only=True, frozen=True, slots=True)
class ReserveNow(Object):

    response_url: URL
    token: Token
    expiry_date: Date
    location_id: str
    evse_uid: str | None = None
    reservation_id: str
    connector_id: str | None = None
    authorization_reference: str | None = None


@define(kw_only=True, frozen=True, slots=True)
class CancelReservation(Object):

    response_url: URL
    reservation_id: str


@define(kw_only=True, frozen=True, slots=True)
class UnlockConnector(Object):

    response_url: URL
    location_id: str
    connector_id: str
    evse_uid: str


@define(kw_only=True, frozen=True, slots=True)
class RIPostCommandParams(Object):

    command: CommandType
    data: StartSession | StopSession | ReserveNow | CancelReservation | UnlockConnector


__all__ = [
    "ReserveNow",
    "CommandType",
    "StopSession",
    "CommandResult",
    "StartSession",
    "CommandResponse",
    "CancelReservation",
    "UnlockConnector",
    "CommandResultType",
    "CommandResponseType",
    "RIPostCommandParams",
]
