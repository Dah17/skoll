import typing as t
from attrs import define, field
from skoll.utils import get_config_var
from ssl import create_default_context
from certifi import where as ssl_where


__all__ = ["SMTPConfig", "JwtConfig", "SSL"]


@define(kw_only=True, slots=True, frozen=True)
class SMTPConfig:

    DEFAULT: t.ClassVar[t.Self]

    host: str = field(factory=get_config_var(keys=["SMTP_HOST"], default=""))
    port: int = field(factory=get_config_var(keys=["SMTP_PORT"], default=465))
    user: str = field(factory=get_config_var(keys=["SMTP_USER"], default=""))
    password: str = field(factory=get_config_var(keys=["SMTP_PASSWORD"], default=""))
    sender_name: str = field(factory=get_config_var(keys=["SMTP_SENDER_NAME"], default=""))
    sender_email: str = field(factory=get_config_var(keys=["SMTP_SENDER_EMAIL"], default=""))


@define(frozen=True, slots=True, kw_only=True)
class JwtConfig:

    DEFAULT: t.ClassVar[t.Self]

    issuer: str = field(factory=get_config_var(keys=["JWT_TOKEN_ISSUER"], default=""))
    encode_key: str = field(factory=get_config_var(keys=["JWT_HASH_SECRET"], default=""))
    decode_key: str = field(factory=get_config_var(keys=["JWT_HASH_SECRET"], default=""))
    audience: str = field(factory=get_config_var(keys=["JWT_TOKEN_AUDIENCE"], default=""))
    algorithm: str = field(factory=get_config_var(keys=["JWT_ALGORITHM"], default="HS256"))


JwtConfig.DEFAULT = JwtConfig()
SMTPConfig.DEFAULT = SMTPConfig()
SSL = create_default_context(cafile=ssl_where())
