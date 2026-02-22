import attrs
import typing as t

from skoll.utils import sanitize_dict


__all__ = [
    "Error",
    "NotFound",
    "Conflict",
    "Forbidden",
    "BadRequest",
    "InvalidField",
    "MissingField",
    "InternalError",
    "Unauthenticated",
    "ValidationFailed",
]

type ErrorStatusCode = t.Literal[400, 401, 403, 404, 405, 409, 429, 500, 502, 503, 504]


@attrs.define(kw_only=True, slots=True)
class Error(Exception):

    code: str
    field: str | None = None
    status: ErrorStatusCode | None = None
    detail: str = "An expected error occurred."
    errors: list["Error"] = attrs.field(factory=list)
    debug: dict[str, t.Any] = attrs.field(factory=dict)
    hints: dict[str, t.Any] = attrs.field(factory=dict)

    def serialize(self, exclude: list[str] | None = None, extra: dict[str, t.Any] | None = None) -> dict[str, t.Any]:
        exclude = exclude or []
        err_json: dict[str, t.Any] = {
            "code": self.code,
            "field": self.field,
            "detail": self.detail,
            "debug": self.debug if "debug" not in exclude else None,
            "hints": self.hints if "hints" not in exclude else None,
            "errors": [sub.serialize(exclude=exclude) for sub in self.errors],
        }
        if extra is not None:
            err_json.update(extra)
        return sanitize_dict(err_json)


@attrs.define(kw_only=True, slots=True)
class MissingField(Error):

    code: str = attrs.field(default="missing_field", init=False)
    hints: dict[str, t.Any] = attrs.field(factory=dict, init=False)
    debug: dict[str, t.Any] = attrs.field(factory=dict, init=False)
    status: ErrorStatusCode | None = attrs.field(default=None, init=False)
    detail: str = attrs.field(default="This field is required to process your request", init=False)


@attrs.define(kw_only=True, slots=True)
class InvalidField(Error):

    code: str = attrs.field(default="invalid_field", init=False)
    debug: dict[str, t.Any] = attrs.field(factory=dict, init=False)
    status: ErrorStatusCode | None = attrs.field(default=None, init=False)
    detail: str = attrs.field(default="This field has invalid data, see hints for more details", init=False)


@attrs.define(kw_only=True, slots=True)
class InternalError(Error):

    field: str | None = attrs.field(default=None, init=False)
    code: str = attrs.field(default="internal_error", init=False)
    hints: dict[str, t.Any] = attrs.field(factory=dict, init=False)
    status: ErrorStatusCode | None = attrs.field(default=500, init=False)
    detail: str = attrs.field(default="An unexpected error occurred. Please try again later.", init=False)

    @classmethod
    def from_exception(cls, exc: Exception, extra: dict[str, t.Any] | None = None) -> t.Self:
        return cls(debug={**(extra or {}), **{"message": str(exc)}})


@attrs.define(kw_only=True, slots=True)
class BadRequest(Error):

    field: str | None = attrs.field(default=None, init=False)
    code: str = attrs.field(default="bad_request", init=False)
    status: ErrorStatusCode | None = attrs.field(default=400, init=False)
    detail: str = attrs.field(default="Your request is invalid. Check hints for more details", init=False)


@attrs.define(kw_only=True, slots=True)
class ValidationFailed(Error):

    field: str | None = attrs.field(default=None, init=False)
    debug: dict[str, t.Any] = attrs.field(factory=dict, init=False)
    code: str = attrs.field(default="validation_failed", init=False)
    status: ErrorStatusCode | None = attrs.field(default=400, init=False)
    detail: str = attrs.field(
        default="Your request contains invalid or missing data. Check hints for more details", init=False
    )


@attrs.define(kw_only=True, slots=True)
class Unauthenticated(Error):

    field: str | None = attrs.field(default=None, init=False)
    code: str = attrs.field(default="unauthenticated", init=False)
    status: ErrorStatusCode | None = attrs.field(default=401, init=False)
    detail: str = attrs.field(default="This request requires is only allowed for authenticated users", init=False)


@attrs.define(kw_only=True, slots=True)
class Forbidden(Error):

    code: str = attrs.field(default="forbidden", init=False)
    field: str | None = attrs.field(default=None, init=False)
    status: ErrorStatusCode | None = attrs.field(default=403, init=False)
    detail: str = attrs.field(
        default="You do not have required privilege for this operation. See hints for more details", init=False
    )


@attrs.define(kw_only=True, slots=True)
class NotFound(Error):

    code: str = attrs.field(default="not_found", init=False)
    field: str | None = attrs.field(default=None, init=False)
    status: ErrorStatusCode | None = attrs.field(default=404, init=False)
    detail: str = attrs.field(default="There is no resource corresponding to your request", init=False)


@attrs.define(kw_only=True, slots=True)
class Conflict(Error):

    code: str = attrs.field(default="conflict", init=False)
    field: str | None = attrs.field(default=None, init=False)
    status: ErrorStatusCode | None = attrs.field(default=409, init=False)
    detail: str = "Can not perform this operation since it will put the system in an inconsistent state"


@attrs.define(kw_only=True, slots=True)
class MissingSubscriber(NotFound):

    attr: str | None = attrs.field(default=None, init=False)
    code: str = attrs.field(default="missing_subscriber", init=False)
    detail: str = attrs.field(default="No subscriber found for the given message subject", init=False)


@attrs.define(kw_only=True, slots=True)
class InvalidToken(Error):

    attr: str | None = attrs.field(default=None, init=False)
    code: str = attrs.field(default="invalid_token", init=False)
    status: ErrorStatusCode | None = attrs.field(default=401, init=False)
    detail: str = attrs.field(default="The provide token is not a valid token", init=False)


@attrs.define(kw_only=True, slots=True)
class ExpiredToken(InvalidToken):

    attr: str | None = attrs.field(default=None, init=False)
    code: str = attrs.field(default="expired_token", init=False)
    detail: str = attrs.field(default="The provide token has expired", init=False)
