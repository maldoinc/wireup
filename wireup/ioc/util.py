import fnmatch
import inspect
import pkgutil
from inspect import Parameter
from types import ModuleType
from typing import Callable, Dict, ItemsView


def get_params_with_default_values(obj: Callable) -> Dict[str, Parameter]:
    params: ItemsView[str, Parameter] = inspect.signature(obj).parameters.items()

    return {name: val for name, val in params if val.default is not Parameter.empty}


def find_classes_in_module(module: ModuleType, pattern: str = "*"):
    for _, modname, __ in pkgutil.walk_packages(module.__path__, prefix=module.__name__ + "."):
        mod = __import__(modname, fromlist="dummy")

        for name in dir(mod):
            obj = getattr(mod, name)

            if isinstance(obj, type) and obj.__module__ == mod.__name__ and fnmatch.fnmatch(obj.__name__, pattern):
                yield obj
