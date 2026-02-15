import typing as t
from attrs import define

from .errors import Error, InvalidField


__all__ = ["Result", "ok", "fail", "is_ok", "is_fail", "combine"]


type Result[T] = _Ok[T] | _Fail
V = t.TypeVar("V", covariant=True)


@define(frozen=True, slots=True)
class _Ok(t.Generic[V]):

    value: V


@define(frozen=True, slots=True)
class _Fail:

    err: Error


def ok(value: V) -> Result[V]:
    return _Ok(value)


def fail(err: Error) -> Result[t.Any]:
    return _Fail(err)


def is_ok[T](res: Result[T]) -> t.TypeIs[_Ok[T]]:
    return isinstance(res, _Ok)


def is_fail[T](res: Result[T]) -> t.TypeIs[_Fail]:
    return isinstance(res, _Fail)


@t.overload
def combine(results: list[Result[t.Any]]) -> Result[list[t.Any]]: ...


@t.overload
def combine(results: dict[str, Result[t.Any]]) -> Result[dict[str, t.Any]]: ...


def combine(results: list[Result[t.Any]] | dict[str, Result[t.Any]]):
    if isinstance(results, dict):
        dict_values = {k: r.value for k, r in results.items() if isinstance(r, _Ok)}
        errs = [r.err for r in results.values() if isinstance(r, _Fail)]
        return _Ok(dict_values) if not errs else _Fail(InvalidField(errors=errs))

    list_values = [r.value for r in results if isinstance(r, _Ok)]
    errs = [r.err for r in results if isinstance(r, _Fail)]
    return _Ok(list_values) if not errs else _Fail(InvalidField(errors=errs))
