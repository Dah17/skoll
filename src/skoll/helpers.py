from aiosmtplib import send
from aiohttp import ClientSession
from email.mime.text import MIMEText
from os import environ as os_environ
from certifi import where as ssl_where


from .result import is_ok
from .domain import IPInfo
from .config import SMTPConfig, SSL

__all__ = ["send_email", "fetch_ip_info"]


async def send_email(to: str, title: str, html_body: str, config: SMTPConfig = SMTPConfig.DEFAULT) -> None:

    os_environ["SSL_CERT_FILE"] = ssl_where()
    sender = f"{config.sender_name} <{config.sender_email}>"
    message = MIMEText(html_body, "html")
    message["Subject"] = title
    message["From"] = sender
    message["To"] = to
    _ = await send(
        message,
        hostname=config.host,
        port=config.port,
        username=config.user,
        password=config.password,
        start_tls=config.start_tls,
        use_tls=not config.start_tls,
    )


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
