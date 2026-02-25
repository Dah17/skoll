import re
import os
import inspect
import functools
import typing as t

from ulid import ulid
from json import loads
from certifi import where
import collections.abc as c
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from ssl import SSLContext, create_default_context


__all__ = [
    "to_tz",
    "new_ulid",
    "safe_call",
    "from_json",
    "serialize",
    "impartial",
    "default_ssl",
    "sanitize_dict",
    "to_camel_case",
    "to_snake_case",
    "get_signature",
    "unwrapped_call",
    "get_config_var",
    "string_to_snake",
    "string_to_camel",
    "to_context_manager",
]

_RE_NON_ALNUM = re.compile(r"[^a-zA-Z0-9]+")
_RE_CAMEL_BOUNDARY_1 = re.compile(r"(.)([A-Z][a-z]+)")
_RE_CAMEL_BOUNDARY_2 = re.compile(r"([a-z0-9])([A-Z])")
default_ssl: SSLContext = create_default_context(cafile=where())

new_ulid: t.Callable[[], str] = lambda: ulid().lower()


def from_json(val: t.Any) -> t.Any:
    try:
        return loads(val)
    except:
        return None


def sanitize_dict(obj: dict[str, t.Any]) -> dict[str, t.Any]:
    return {
        k: sanitize_dict(t.cast(dict[str, t.Any], v)) if isinstance(v, dict) else v
        for k, v in obj.items()
        if v is not None
    }


def string_to_snake(value: str) -> str:
    if not value:
        return value

    value = _RE_NON_ALNUM.sub("_", value)
    value = _RE_CAMEL_BOUNDARY_1.sub(r"\1_\2", value)
    value = _RE_CAMEL_BOUNDARY_2.sub(r"\1_\2", value)
    value = re.sub(r"_+", "_", value)

    return value.strip("_").lower()


def string_to_camel(value: str, *, pascal: bool = False) -> str:
    if not value:
        return value

    value = _RE_NON_ALNUM.sub("_", value)
    parts = [p for p in value.split("_") if p]

    if not parts:
        return ""

    if pascal:
        return "".join(p.capitalize() for p in parts)

    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def to_snake_case(val: t.Any) -> t.Any:
    if isinstance(val, dict):
        return {string_to_snake(k) if isinstance(k, str) else k: to_snake_case(v) for k, v in val.items()}

    if isinstance(val, (list, tuple)):
        return [to_snake_case(i) for i in val]

    return val


def to_camel_case(val: t.Any, *, pascal: bool = False) -> t.Any:
    if isinstance(val, dict):
        return {
            string_to_camel(k, pascal=pascal) if isinstance(k, str) else k: to_camel_case(v, pascal=pascal)
            for k, v in val.items()
        }

    if isinstance(val, (list, tuple)):
        return [to_camel_case(i, pascal=pascal) for i in val]

    return val


def serialize(data: t.Any) -> t.Any:
    if hasattr(data, "serialize") and callable(getattr(data, "serialize")):
        return data.serialize()
    if isinstance(data, (list, tuple)):
        return [serialize(x) for x in data]
    if isinstance(data, dict):
        res_dict = {}
        for key, value in data.items():
            res_dict[key] = serialize(value)
        return res_dict
    return data


def iso_to_timestamp(date_string: str, format: str = "%Y-%m-%dT%H:%M:%SZ"):
    dt = datetime.strptime(date_string, format)
    dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def timestamp_to_iso(timestamp: int, format: str = "%Y-%m-%dT%H:%M:%SZ") -> str:
    dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
    return dt.strftime(format)


def find_item[T](match_with: t.Callable[[T], bool], items: list[T]) -> T | None:
    found_item: T | None = None
    for item in items:
        if match_with(item):
            found_item = item
            break
    return found_item


def to_tz(tz_str: str) -> ZoneInfo:
    try:
        return ZoneInfo(key=tz_str)
    except:
        return ZoneInfo("UTC")


def names_from_email(email: str) -> tuple[str, str]:
    names = email.split("@")[0].split(".")
    if len(names) == 0:
        return "", ""
    if len(names) == 1:
        return names[0], ""
    return " ".join(names[:-1]), names[-1]


def safe_call[T](func: t.Callable[..., T], *args: t.Any, **kwargs: t.Any) -> T | None:
    try:
        return func(*args, **kwargs)
    except:
        return None


@asynccontextmanager
async def to_context_manager(gen: c.AsyncGenerator[t.Any, t.Any]):
    try:
        value = await gen.__anext__()
        yield value
    finally:
        await gen.aclose()


def get_signature(fn: t.Callable[..., t.Any]) -> list[inspect.Parameter]:
    unwrapped = unwrapped_call(fn)
    if unwrapped is None:
        return []
    return list(inspect.signature(unwrapped).parameters.values())


def unwrapped_call(call: t.Callable[..., t.Any] | None) -> t.Callable[..., t.Any] | None:
    if call is None:
        return call
    unwrapped = inspect.unwrap(impartial(call))
    return unwrapped


def impartial(func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
    while isinstance(func, functools.partial):
        func = func.func
    return func


def get_config_var[T](keys: list[str], default: T) -> t.Callable[[], T]:

    def get_var() -> T:
        for key in keys:
            if "/" in key:
                with open(key, "r") as f:
                    return t.cast(T, f.read().strip())
            value = os.getenv(key)
            if value:
                return t.cast(T, value)
        return default

    return get_var
