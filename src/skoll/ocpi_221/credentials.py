from attrs import define, field

from skoll.domain import Object

from .base import URL, Role, PartyID, CountryCode, BusinessDetails


@define(kw_only=True, frozen=True, slots=True)
class CredentialsRole(Object):

    role: Role
    party_id: PartyID
    country_code: CountryCode
    business_details: BusinessDetails


@define(kw_only=True, frozen=True, slots=True)
class Credentials(Object):

    url: URL
    token: str
    roles: list[CredentialsRole] = field(factory=list)


@define(kw_only=True, frozen=True, slots=True)
class PartialCredentials(Object):

    url: URL | None = None
    token: str | None = None
    roles: list[CredentialsRole] | None = None


__all__ = ["Credentials", "CredentialsRole", "PartialCredentials"]
