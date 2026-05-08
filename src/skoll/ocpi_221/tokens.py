from attrs import define

from skoll.domain import Enum, Object

from .base import Date, PartyID, CountryCode


class WhitelistType(Enum):

    ALWAYS = "ALWAYS"
    ALLOWED = "ALLOWED"
    ALLOWED_OFFLINE = "ALLOWED_OFFLINE"
    NEVER = "NEVER"


class TokenType(Enum):

    AD_HOC_USER = "AD_HOC_USER"
    APP_USER = "APP_USER"
    OTHER = "OTHER"
    RFID = "RFID"


class AuthMethod(Enum):

    AUTH_REQUEST = "AUTH_REQUEST"
    COMMAND = "COMMAND"
    WHITELIST = "WHITELIST"


@define(kw_only=True, frozen=True, slots=True)
class EnergyContract(Object):

    contract_id: str
    supplier_name: str


@define(kw_only=True, frozen=True, slots=True)
class Token(Object):

    country_code: CountryCode
    party_id: PartyID
    uid: str
    type: TokenType
    contract_id: str
    visual_number: str | None = None
    issuer: str
    group_id: str | None = None
    valid: bool
    whitelist: WhitelistType
    language: str | None = None
    default_profile_type: str | None = None
    energy_contract: EnergyContract | None = None
    last_updated: Date


@define(kw_only=True, frozen=True, slots=True)
class PartialToken(Object):

    country_code: CountryCode | None = None
    party_id: PartyID | None = None
    uid: str | None = None
    type: TokenType | None = None
    contract_id: str | None = None
    visual_number: str | None = None
    issuer: str | None = None
    group_id: str | None = None
    valid: bool | None = None
    whitelist: WhitelistType | None = None
    language: str | None = None
    default_profile_type: str | None = None
    energy_contract: EnergyContract | None = None
    last_updated: Date | None = None


@define(kw_only=True, frozen=True, slots=True)
class ListTokensParams(Object):

    date_from: Date | None = None
    date_to: Date | None = None
    offset: int | None = None
    limit: int | None = None


@define(kw_only=True, frozen=True, slots=True)
class GetTokenParams(Object):

    token_uid: str
    type: TokenType


__all__ = [
    "Token",
    "AuthMethod",
    "TokenType",
    "PartialToken",
    "WhitelistType",
    "GetTokenParams",
    "EnergyContract",
    "ListTokensParams",
]
