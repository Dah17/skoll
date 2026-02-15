import attrs
import typing as t
from abc import ABC
from types import UnionType
from enum import Enum as _Enum


from skoll.utils import to_snake_case, serialize
from skoll.errors import MissingField, InvalidField, Error
from skoll.result import Result, fail, ok, combine, is_fail, is_ok


__all__ = ["Enum", "Object"]


class Enum(_Enum):

    def serialize(self) -> str:
        return self.value

    @classmethod
    def options(cls) -> list[str]:
        return [option.value for option in list(cls)]

    @classmethod
    def create(cls, raw: t.Any) -> Result[t.Self]:
        if raw in cls.options():
            return ok(cls(raw))

        if raw is None:
            return fail(MissingField(field=to_snake_case(cls.__name__)))

        return fail(
            Error(
                code="unknown_option",
                field=to_snake_case(cls.__name__),
                hints={"expected": cls.options(), "received": raw},
                detail=f"Invalid input passed, check the hints for more details.",
            )
        )


@attrs.define(kw_only=True, frozen=True, slots=True)
class Object(ABC):

    def serialize(self) -> t.Any:
        data = {f.name: getattr(self, f.name) for f in attrs.fields(self.__class__)}
        if len(data) == 1 and data.get("value") is not None:
            return serialize(data["value"])
        return serialize(data)

    @classmethod
    def prepare(cls, raw: t.Any) -> Result[t.Any]:
        return ok(raw)

    @classmethod
    def _init(cls, value: t.Any) -> Result[t.Self]:
        if isinstance(value, dict):
            return ok(cls(**value))
        return ok(cls(**{"value": value}))

    @classmethod
    def create(cls, raw: t.Any) -> Result[t.Self]:
        if raw is None:
            return fail(MissingField(field=to_snake_case(cls.__name__)))

        prepare_result = cls.prepare(raw)
        if is_fail(prepare_result):
            return prepare_result

        schema = get_schema(cls)
        if schema is None:
            return cls._init(prepare_result.value)

        results: dict[str, Result[t.Any]] = {}
        for key, item in schema.items():
            results[key] = item.create(prepare_result.value)
        res = combine(results)
        return cls._init(**res.value) if is_ok(res) else res

    def evolve(self, **kwargs: t.Any) -> t.Self:
        return attrs.evolve(self, **kwargs)


@attrs.define(kw_only=True, slots=True, frozen=True)
class _SchemaItem:
    """
    Represents a single item in object schema.
    """

    key: str
    cls: t.Any
    is_list: bool = False
    optional: bool = False
    default: t.Any = attrs.NOTHING

    def create(self, raw: t.Any) -> Result[t.Any]:
        raw_item = raw.get(self.key) if isinstance(raw, dict) else raw
        if raw_item is None and self.default != attrs.NOTHING:
            if not hasattr(self.default, "factory"):
                return ok(value=self.default)
            if self.default.takes_self is False:
                return ok(value=self.default.factory())
            # Ignore case where takes_self is True, as we don't have the object instance here

        if self.optional is True and raw_item is None:
            return ok(value=None)
        if raw_item is None:
            return fail(MissingField(field=self.key))
        if self.is_list and isinstance(raw_item, list):
            results: list[Result[t.Any]] = []
            for idx, rw in enumerate(t.cast(list[t.Any], raw_item)):
                res = self._create(raw=rw, field=f"{self.key}[{idx}]")
                results.append(res)
            res = combine(results)
            if is_fail(res):
                res.err.field = self.key
            return res
        if self.is_list and not isinstance(raw_item, list):
            return fail(InvalidField(field=self.key))
        return self._create(raw=raw_item)

    def _create(self, raw: t.Any, field: str | None = None) -> Result[t.Any]:
        field = field or self.key
        if hasattr(self.cls, "create") and callable(getattr(self.cls, "create")):
            return self.cls.create(raw)

        type_checkers: dict[type[t.Any], t.Callable[[t.Any], bool]] = {
            bool: lambda x: x in ["True", "False", True, False],
            str: lambda x: isinstance(x, (str, float, int)),
            int: lambda x: isinstance(x, (int, float)),
            float: lambda x: isinstance(x, (float, int)),
        }
        check = type_checkers.get(self.cls)

        if check is None or check(raw) is True:
            return ok(raw if check is None else self.cls(raw))

        return fail(InvalidField(field=field, hints={"expected": self.cls.__name__, "received": raw}))


def get_schema(cls: type[t.Any]) -> dict[str, _SchemaItem] | None:
    if not attrs.has(cls) or (len(attrs.fields(cls)) == 1 and attrs.fields(cls)[0].name == "value"):
        return None

    schema: dict[str, _SchemaItem] = {}
    for key, attr in attrs.fields_dict(cls).items():
        is_list, optional, _cls = False, False, attr.type
        if t.get_origin(_cls) == UnionType and t.get_args(_cls)[1] == type(None):
            _cls = t.get_args(attr.type)[0]
            optional = True
        if t.get_origin(_cls) == list:
            is_list = True
            _cls = t.get_args(attr.type)[0]

        schema[key] = _SchemaItem(key=key, cls=_cls, is_list=is_list, optional=optional, default=attr.default)
    return schema
