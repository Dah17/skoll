import attrs
import typing as t
from abc import ABC
from types import UnionType
from enum import Enum as _Enum


from skoll.utils import to_snake_case, serialize, safe_call
from skoll.exceptions import MissingField, InvalidField, Error
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
        return cls._init(value=res.value) if is_ok(res) else res

    def evolve(self, allow_none: bool = False, **kwargs: t.Any) -> t.Self:
        allowed_keys = {f.name for f in attrs.fields(self.__class__)}
        keys_to_remove = [key for key in kwargs if key not in allowed_keys or (kwargs[key] is None and not allow_none)]
        for k in keys_to_remove:
            del kwargs[k]
        return attrs.evolve(self, **kwargs)


@attrs.define(kw_only=True, slots=True, frozen=True)
class _SchemaItem:
    """
    Represents a single item in object schema.
    """

    key: str
    types: tuple[t.Any, ...]
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

        errors: list[Result[t.Any]] = []
        for item_type in self.types:
            res = self._create(raw=raw_item, cls=item_type, field=self.key)
            if is_ok(res):
                return res
            errors.append(res)

        return fail(
            InvalidField(
                field=self.key,
                hints={
                    "expected": [_type_to_name(item_type) for item_type in self.types],
                    "received": raw_item,
                },
            )
        )

    def _create(self, raw: t.Any, cls: t.Any, field: str | None = None) -> Result[t.Any]:
        field = field or self.key
        origin = t.get_origin(cls)
        args = t.get_args(cls)

        if origin == list:
            if not isinstance(raw, list):
                return fail(InvalidField(field=field))
            item_type = args[0] if len(args) == 1 else t.Any
            results: list[Result[t.Any]] = []
            for idx, value in enumerate(t.cast(list[t.Any], raw)):
                results.append(self._create(raw=value, cls=item_type, field=f"{field}[{idx}]"))
            res = combine(results)
            if is_fail(res):
                res.err.field = field
            return res

        if origin == dict:
            if not isinstance(raw, dict):
                return fail(InvalidField(field=field))
            key_type = args[0] if len(args) >= 1 else t.Any
            value_type = args[1] if len(args) >= 2 else t.Any
            parsed: dict[t.Any, t.Any] = {}
            for raw_key, raw_value in t.cast(dict[t.Any, t.Any], raw).items():
                key_res = self._create(raw=raw_key, cls=key_type, field=f"{field}.key")
                if is_fail(key_res):
                    return key_res
                value_res = self._create(raw=raw_value, cls=value_type, field=f"{field}[{raw_key}]")
                if is_fail(value_res):
                    return value_res
                parsed[key_res.value] = value_res.value
            return ok(parsed)

        if origin == tuple:
            if not isinstance(raw, tuple):
                return fail(InvalidField(field=field))
            raw_tuple = t.cast(tuple[t.Any, ...], raw)
            if len(args) == 2 and args[1] is Ellipsis:
                item_type = args[0]
                results = [
                    self._create(raw=value, cls=item_type, field=f"{field}[{idx}]")
                    for idx, value in enumerate(raw_tuple)
                ]
                res = combine(results)
                if is_fail(res):
                    res.err.field = field
                    return res
                return ok(tuple(res.value))
            if args and len(args) != len(raw_tuple):
                return fail(InvalidField(field=field))

            result_values: list[t.Any] = []
            for idx, value in enumerate(raw_tuple):
                item_type = args[idx] if args else t.Any
                res = self._create(raw=value, cls=item_type, field=f"{field}[{idx}]")
                if is_fail(res):
                    return res
                result_values.append(res.value)
            return ok(tuple(result_values))

        if origin == UnionType:
            union_types = tuple(item for item in args if item is not type(None))
            for item_type in union_types:
                res = self._create(raw=raw, cls=item_type, field=field)
                if is_ok(res):
                    return res
            return fail(InvalidField(field=field))

        if hasattr(cls, "create") and callable(getattr(cls, "create")):
            return cls.create(raw)

        if cls in {list, dict, tuple}:
            if isinstance(raw, cls):
                return ok(raw)
            return fail(InvalidField(field=field, hints={"expected": cls.__name__, "received": raw}))

        type_checkers: dict[type[t.Any], t.Callable[[t.Any], bool]] = {
            bool: lambda x: x in ["True", "False", True, False],
            str: lambda x: isinstance(x, (str, float, int)),
            int: lambda x: isinstance(x, (int, float, str)),
            float: lambda x: isinstance(x, (float, int, str)),
        }
        check = type_checkers.get(cls)

        if check is None:
            return ok(raw)
        if check(raw) is True:
            value = safe_call(cls, raw)
            if value is not None:
                return ok(value)

        return fail(InvalidField(field=field, hints={"expected": cls.__name__, "received": raw}))


def _split_types(tp: t.Any) -> tuple[t.Any, ...]:
    origin = t.get_origin(tp)
    if origin == UnionType:
        types: list[t.Any] = []
        for item in t.get_args(tp):
            types.extend(_split_types(item))
        return tuple(types)
    return (tp,)


def _type_to_name(tp: t.Any) -> str:
    origin = t.get_origin(tp)
    args = t.get_args(tp)
    if origin == list:
        item = _type_to_name(args[0]) if args else "Any"
        return f"list[{item}]"
    if origin == dict:
        key = _type_to_name(args[0]) if len(args) >= 1 else "Any"
        value = _type_to_name(args[1]) if len(args) >= 2 else "Any"
        return f"dict[{key}, {value}]"
    if origin == tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return f"tuple[{_type_to_name(args[0])}, ...]"
        values = ", ".join(_type_to_name(item) for item in args) if args else ""
        return f"tuple[{values}]" if values else "tuple"
    if origin == UnionType:
        return " | ".join(_type_to_name(item) for item in args)
    if tp is type(None):
        return "None"
    if hasattr(tp, "__name__"):
        return tp.__name__
    return str(tp)


def get_schema(cls: type[t.Any]) -> dict[str, _SchemaItem] | None:
    if not attrs.has(cls) or (len(attrs.fields(cls)) == 1 and attrs.fields(cls)[0].name == "value"):
        return None

    schema: dict[str, _SchemaItem] = {}
    for key, attr in attrs.fields_dict(cls).items():
        variants = _split_types(attr.type)
        optional = type(None) in variants
        types = tuple(item for item in variants if item is not type(None))
        schema[key] = _SchemaItem(
            key=key,
            optional=optional,
            default=attr.default,
            types=types if types else (t.Any,),
        )
    return schema
