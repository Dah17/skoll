import typing as t

from .primitives import DateTime, Ulid
from .ports import Clock, IdGenerator, CodeGenerator


class SystemClock(Clock):

    @t.override
    def now(self) -> DateTime:
        return DateTime.now()


class UlidGenerator(IdGenerator[Ulid]):

    @t.override
    def generate(self) -> Ulid:
        return Ulid()


class FixedClock(Clock):

    _now: DateTime

    def __init__(self, now: DateTime) -> None:
        self._now = now

    @t.override
    def now(self) -> DateTime:
        return self._now


class FixedUlidGenerator(IdGenerator[Ulid]):

    _idx: int
    _ids: list[Ulid]

    def __init__(self, *ids: Ulid):
        self._ids = list(ids)
        self._idx = 0

    @t.override
    def generate(self) -> Ulid:
        if self._idx >= len(self._ids):
            raise AssertionError(
                f"FixedUlidGenerator exhausted: test supplied {len(self._ids)} id(s) but generate() was called {self._idx + 1} times"
            )
        uid = self._ids[self._idx]
        self._idx += 1
        return uid


class FixedCodeGenerator(CodeGenerator):

    _code: str

    def __init__(self, code: str) -> None:
        self._code = code

    @t.override
    def generate(self) -> str:
        return self._code


__all__ = ["SystemClock", "UlidGenerator", "FixedClock", "FixedUlidGenerator", "FixedCodeGenerator"]
