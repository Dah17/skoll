import inspect
import typing as t
from attrs import define
import collections.abc as c
from contextlib import AsyncExitStack, AbstractAsyncContextManager

from .functional import to_context_manager, get_signature


type Cache = dict[t.Any, t.Any]
type Context = dict[str, t.Any]
type DepFn = t.Callable[..., t.Any]
type BaseFn[T] = t.Callable[..., c.Coroutine[t.Any, t.Any, T]]


__all__ = [
    "depend",
    "resolve",
    "Dependent",
    "get_dependant",
    "call_with_dependencies",
]


@define(slots=True, kw_only=True)
class Dependent:

    call: t.Callable[..., t.Any]


def depend(call: t.Callable[..., t.Any]) -> Dependent:
    return Dependent(call=call)


async def call_with_dependencies[T](fn: BaseFn[T], context: Context | None = None) -> T:
    async with AsyncExitStack() as stack:
        kwargs = await resolve(fn, cache={}, context=context or {}, exit_stack=stack, no_call=True)
        return await fn(**kwargs)


def get_dependant(annotation: t.Any) -> Dependent | None:
    if t.get_origin(annotation) is not t.Annotated:
        return None

    _, *metadata = t.get_args(annotation)
    for meta in metadata:
        if isinstance(meta, Dependent):
            return meta
    return None


async def resolve(
    fn: DepFn, cache: Cache, context: Context, exit_stack: AsyncExitStack, no_call: bool = False
) -> t.Any:
    if fn in cache:
        return cache[fn]

    kwargs: dict[str, t.Any] = {}

    for param in get_signature(fn):
        if context.get(param.name) is not None:
            kwargs[param.name] = context[param.name]
            continue

        dep = get_dependant(param.annotation)
        if dep is not None:
            kwargs[param.name] = await resolve(dep.call, cache=cache, context=context, exit_stack=exit_stack)
            continue

        if param.default is inspect.Parameter.empty:
            raise TypeError(f"Unresolvable dependency parameter: {param.name}")

        kwargs[param.name] = param.default

    if no_call:
        return kwargs

    result: t.Any = fn(**kwargs)
    result = to_context_manager(result) if inspect.isasyncgen(result) else result

    if isinstance(result, AbstractAsyncContextManager):
        value = await exit_stack.enter_async_context(result)
    elif inspect.isawaitable(result):
        value = await result
    else:
        value = result

    cache[fn] = value
    return value
