from aiosmtplib import send
from attrs import define, field
from email.mime.text import MIMEText
from certifi import where as ssl_where
from os import environ as os_environ, getenv


@define(kw_only=True, slots=True, frozen=True)
class SMTPConfig:

    host: str = field(factory=lambda: getenv("SMTP_HOST", ""))
    user: str = field(factory=lambda: getenv("SMTP_USER", ""))
    port: int = field(factory=lambda: int(getenv("SMTP_PORT", 465)))
    password: str = field(factory=lambda: getenv("SMTP_PASSWORD", ""))
    sender_name: str = field(factory=lambda: getenv("SMTP_SENDER_NAME", ""))
    sender_email: str = field(factory=lambda: getenv("SMTP_SENDER_EMAIL", ""))


DEFAULT_CONFIG = SMTPConfig()


async def send_email(to: str, title: str, html_body: str, config: SMTPConfig = DEFAULT_CONFIG) -> None:

    os_environ["SSL_CERT_FILE"] = ssl_where()
    sender = f"{config.sender_name} <{config.sender_email}>"
    message = MIMEText(html_body, "html")
    message["Subject"] = title
    message["From"] = sender
    message["To"] = to
    _ = await send(
        message, hostname=config.host, port=config.port, username=config.user, password=config.password, use_tls=True
    )
