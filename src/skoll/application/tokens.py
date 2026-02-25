import os
import jwt
import typing as t

from calendar import timegm
from attrs import define, field
from skoll.errors import InternalError
from skoll.utils import get_config_var
from skoll.result import Result, fail, ok
from datetime import datetime as dt, timedelta, UTC


__all__ = ["DecodedJwtToken", "JwtConfig", "create_jwt_token", "decode_jwt_token"]


class DecodedJwtToken(t.NamedTuple):

    expired: bool = False
    invalid: bool = False
    sub: str | None = None
    kind: str | None = None
    extra: dict[str, t.Any] | None = None


@define(frozen=True, slots=True, kw_only=True)
class JwtConfig:

    issuer: str = field(factory=get_config_var(keys=["JWT_TOKEN_ISSUER"], default=""))
    encode_key: str = field(factory=get_config_var(keys=["JWT_HASH_SECRET"], default=""))
    decode_key: str = field(factory=get_config_var(keys=["JWT_HASH_SECRET"], default=""))
    audience: str = field(factory=get_config_var(keys=["JWT_TOKEN_AUDIENCE"], default=""))
    algorithm: str = field(factory=get_config_var(keys=["JWT_ALGORITHM"], default="HS256"))


DEFAULT_CONFIG = JwtConfig()


def create_jwt_token(
    sub: str, kind: str, duration_min: int, extra: dict[str, t.Any] | None = None, config: JwtConfig = DEFAULT_CONFIG
) -> Result[str]:
    try:
        iat = dt.now(tz=UTC)
        exp = iat + timedelta(minutes=duration_min)
        payload = {
            "sub": sub,
            "kind": kind,
            "extra": extra or {},
            "iss": config.issuer,
            "aud": config.audience,
            "exp": timegm(exp.utctimetuple()),
            "iat": timegm(iat.utctimetuple()),
        }
        return ok(value=jwt.encode(payload=payload, key=config.encode_key, algorithm=config.algorithm))
    except Exception as e:
        return fail(err=InternalError.from_exception(e))


def decode_jwt_token(token: str, kind: str, config: JwtConfig = DEFAULT_CONFIG) -> DecodedJwtToken:
    try:
        params: dict[str, t.Any] = {
            "jwt": token,
            "issuer": config.issuer,
            "key": config.decode_key,
            "audience": config.audience,
            "algorithms": [config.algorithm],
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
