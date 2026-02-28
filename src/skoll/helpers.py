import jwt
import typing as t

from calendar import timegm
from aiosmtplib import send
from aiohttp import ClientSession
from email.mime.text import MIMEText
from os import environ as os_environ
from certifi import where as ssl_where
from datetime import datetime as dt, timedelta, UTC


from .exceptions import InternalError
from .result import Result, fail, ok, is_ok
from .domain import DecodedJwtToken, IPInfo
from .config import SMTPConfig, JwtConfig, SSL


__all__ = ["send_email", "decode_jwt_token", "create_jwt_token", "fetch_ip_info"]


async def send_email(to: str, title: str, html_body: str, config: SMTPConfig = SMTPConfig.DEFAULT) -> None:

    os_environ["SSL_CERT_FILE"] = ssl_where()
    sender = f"{config.sender_name} <{config.sender_email}>"
    message = MIMEText(html_body, "html")
    message["Subject"] = title
    message["From"] = sender
    message["To"] = to
    _ = await send(
        message, hostname=config.host, port=config.port, username=config.user, password=config.password, use_tls=True
    )


def decode_jwt_token(token: str, kind: str, config: JwtConfig = JwtConfig.DEFAULT) -> DecodedJwtToken:
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


def create_jwt_token(
    sub: str, kind: str, duration_min: int, extra: dict[str, t.Any] | None = None, config: JwtConfig = JwtConfig.DEFAULT
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


async def fetch_ip_info(ip: str) -> IPInfo | None:
    try:
        async with ClientSession() as session:
            async with session.get(f"https://ipinfo.io/{ip}/json", ssl=SSL) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                raw = {
                    "city": data.get("city"),
                    "country_code": data.get("country"),
                    "region_code": data.get("region_code"),
                    "timezone": data.get("timezone", "UTC"),
                    "currency": data.get("currency", "EUR"),
                }
                res = IPInfo.create(raw)
                return res.value if is_ok(res) else None
    except:
        return None
