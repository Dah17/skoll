from aiosmtplib import send
from attrs import define, field
from email.mime.text import MIMEText
from os import environ as os_environ
from certifi import where as ssl_where
from skoll.utils import get_config_var


__all__ = ["SMTPConfig", "send_email"]


@define(kw_only=True, slots=True, frozen=True)
class SMTPConfig:

    host: str = field(factory=get_config_var(keys=["SMTP_HOST"], default=""))
    user: str = field(factory=get_config_var(keys=["SMTP_USER"], default=""))
    port: int = field(factory=get_config_var(keys=["SMTP_PORT"], default=465))
    password: str = field(factory=get_config_var(keys=["SMTP_PASSWORD"], default=""))
    sender_name: str = field(factory=get_config_var(keys=["SMTP_SENDER_NAME"], default=""))
    sender_email: str = field(factory=get_config_var(keys=["SMTP_SENDER_EMAIL"], default=""))


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
