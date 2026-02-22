import os
import jwt
import typing as t

from calendar import timegm
from skoll.errors import InternalError
from skoll.result import Result, fail, ok
from datetime import datetime as dt, timedelta, UTC


__all__ = ["DecodedJwtToken", "encode_jwt_token", "decode_jwt_token"]


ALGO = os.getenv("JWT_ALGORITHM", "HS256")
JWT_HASH_SECRET = os.getenv("JWT_HASH_SECRET", "")
JWT_TOKEN_ISSUER = os.getenv("JWT_TOKEN_ISSUER", "")
JWT_TOKEN_AUDIENCE = os.getenv("JWT_TOKEN_AUDIENCE", "")
JWT_ACCESS_TOKEN_DURATION = int(os.getenv("JWT_ACCESS_TOKEN_DURATION_MIN", "1"))
JWT_REFRESH_TOKEN_DURATION = int(os.getenv("JWT_REFRESH_TOKEN_DURATION_DAY", "1"))


class DecodedJwtToken(t.NamedTuple):

    expired: bool = False
    invalid: bool = False
    data: dict[str, t.Any] | None = None


def encode_jwt_token(sub: str, duration: int, **kwargs: t.Any) -> Result[str]:
    try:
        iat = dt.now(tz=UTC)
        exp = iat + timedelta(seconds=duration)
        payload = {
            **kwargs,
            "sub": sub,
            "iss": JWT_TOKEN_ISSUER,
            "aud": JWT_TOKEN_AUDIENCE,
            "exp": timegm(exp.utctimetuple()),
            "iat": timegm(iat.utctimetuple()),
        }
        return ok(value=jwt.encode(payload=payload, key=JWT_HASH_SECRET, algorithm=ALGO))
    except Exception as e:
        return fail(err=InternalError.from_exception(e))


def decode_jwt_token(token: str) -> DecodedJwtToken:
    try:
        params: dict[str, t.Any] = {
            "jwt": token,
            "algorithms": [ALGO],
            "key": JWT_HASH_SECRET,
            "issuer": JWT_TOKEN_ISSUER,
            "audience": JWT_TOKEN_AUDIENCE,
        }
        data = jwt.decode(**params)
        return DecodedJwtToken(data=data)
    except jwt.ExpiredSignatureError:
        return DecodedJwtToken(expired=True)
    except Exception:
        return DecodedJwtToken(invalid=True)
