from attrs import define, field

from skoll.domain import Object

from .base import URL, Role


@define(kw_only=True, frozen=True, slots=True)
class Version(Object):

    url: URL
    version: str


@define(kw_only=True, frozen=True, slots=True)
class VersionEndpoint(Object):

    url: URL
    identifier: str
    role: Role


@define(kw_only=True, frozen=True, slots=True)
class VersionDetails(Object):

    version: str
    endpoints: list[VersionEndpoint] = field(factory=list)


__all__ = ["Version", "VersionDetails", "VersionEndpoint"]
