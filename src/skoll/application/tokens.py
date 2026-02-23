import os
import jwt
import typing as t

from calendar import timegm
from attrs import define, field
from skoll.errors import InternalError
from skoll.result import Result, fail, ok
from datetime import datetime as dt, timedelta, UTC


__all__ = ["DecodedJwtToken", "JwtConfig", "JwtToken"]


class DecodedJwtToken(t.NamedTuple):

    expired: bool = False
    invalid: bool = False
    sub: str | None = None
    kind: str | None = None
    extra: dict[str, t.Any] | None = None


@define(frozen=True, slots=True, kw_only=True)
class JwtConfig:

    issuer: str = field(factory=lambda: os.getenv("JWT_TOKEN_ISSUER", ""))
    encode_key: str = field(factory=lambda: os.getenv("JWT_HASH_SECRET", ""))
    decode_key: str = field(factory=lambda: os.getenv("JWT_HASH_SECRET", ""))
    audience: str = field(factory=lambda: os.getenv("JWT_TOKEN_AUDIENCE", ""))
    algorithm: str = field(factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))


@define(frozen=True, slots=True, kw_only=True)
class JwtToken:

    config: JwtConfig = field(factory=lambda: JwtConfig())

    def new(self, sub: str, kind: str, duration_min: int, extra: dict[str, t.Any] | None = None) -> Result[str]:
        try:
            iat = dt.now(tz=UTC)
            exp = iat + timedelta(minutes=duration_min)
            payload = {
                "sub": sub,
                "kind": kind,
                "extra": extra or {},
                "iss": self.config.issuer,
                "aud": self.config.audience,
                "exp": timegm(exp.utctimetuple()),
                "iat": timegm(iat.utctimetuple()),
            }
            return ok(value=jwt.encode(payload=payload, key=self.config.encode_key, algorithm=self.config.algorithm))
        except Exception as e:
            return fail(err=InternalError.from_exception(e))

    def decode(self, token: str, kind: str) -> DecodedJwtToken:
        try:
            params: dict[str, t.Any] = {
                "jwt": token,
                "issuer": self.config.issuer,
                "key": self.config.decode_key,
                "audience": self.config.audience,
                "algorithms": [self.config.algorithm],
            }
            payload = jwt.decode(**params)
            kind, sub, extra = payload.get("kind", ""), payload.get("sub", ""), payload.get("extra", {})
            if kind != kind or not sub:
                return DecodedJwtToken(invalid=True)
            return DecodedJwtToken(sub=sub, kind=kind, extra=extra)
        except jwt.ExpiredSignatureError:
            return DecodedJwtToken(expired=True)
        except Exception:
            return DecodedJwtToken(invalid=True)
