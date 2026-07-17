import typing as t
from attrs import define, field
from skoll.utils import get_config_var
from ssl import create_default_context
from certifi import where as ssl_where

__all__ = ["SMTPConfig", "SSL"]


@define(kw_only=True, slots=True, frozen=True)
class SMTPConfig:

    DEFAULT: t.ClassVar[t.Self]

    host: str = field(factory=get_config_var(keys=["SMTP_HOST"], default=""))
    user: str = field(factory=get_config_var(keys=["SMTP_USER"], default=""))
    password: str = field(factory=get_config_var(keys=["SMTP_PASSWORD"], default=""))
    sender_name: str = field(factory=get_config_var(keys=["SMTP_SENDER_NAME"], default=""))
    port: int = field(factory=lambda: int(get_config_var(keys=["SMTP_PORT"], default=465)()))
    sender_email: str = field(factory=get_config_var(keys=["SMTP_SENDER_EMAIL"], default=""))
    start_tls: bool = field(factory=lambda: bool(get_config_var(keys=["SMTP_START_TLS"], default="False")))


SMTPConfig.DEFAULT = SMTPConfig()
SSL = create_default_context(cafile=ssl_where())
