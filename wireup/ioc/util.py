from __future__ import annotations

import fnmatch
import inspect
import pkgutil
from inspect import Parameter
from typing import TYPE_CHECKING, Callable, Generator, ItemsView

if TYPE_CHECKING:
    from types import ModuleType


def get_params_with_default_values(obj: Callable) -> dict[str, Parameter]:
    params: ItemsView[str, Parameter] = inspect.signature(obj).parameters.items()

    return {name: val for name, val in params if val.default is not Parameter.empty}


def find_classes_in_module(module: ModuleType, pattern: str = "*") -> Generator[type, None, None]:
    for _, modname, __ in pkgutil.walk_packages(module.__path__, prefix=module.__name__ + "."):
        mod = __import__(modname, fromlist="dummy")

        for name in dir(mod):
            obj = getattr(mod, name)

            if isinstance(obj, type) and obj.__module__ == mod.__name__ and fnmatch.fnmatch(obj.__name__, pattern):
                yield obj
