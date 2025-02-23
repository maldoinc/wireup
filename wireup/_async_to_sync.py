import copy
import functools
import inspect
import textwrap
import types
from typing import Any, Awaitable, Callable, Mapping, TypeVar, cast

from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


def async_to_sync(new_name: str, func: Callable[P, Awaitable[T]], replacements: Mapping[Any, Any]) -> Callable[P, T]:
    source = textwrap.dedent(inspect.getsource(func))
    for async_fn, sync_fn in replacements.items():
        source = source.replace(f"await self.{async_fn.__name__}", f"self.{sync_fn.__name__}")

    source = source.replace("async def", "def")

    code = compile(source, filename="<string>", mode="exec")
    namespace: dict[str, object] = {}
    exec(code, func.__globals__, namespace)  # noqa: S102
    sync_func: types.FunctionType = cast(types.FunctionType, namespace[func.__name__])

    sync_func.__name__ = new_name
    sync_func.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
    sync_func.__dict__.update(copy.deepcopy(func.__dict__))
    sync_func = functools.update_wrapper(sync_func, func)  # type: ignore[assignment]
    sync_func.__kwdefaults__ = func.__kwdefaults__

    return sync_func
