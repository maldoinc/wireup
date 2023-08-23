import builtins
import fnmatch
import inspect
import pkgutil
from inspect import Parameter
from types import ModuleType
from typing import Any, Callable, Dict, ItemsView, Type, Union


def is_builtin_class(class_type):
    return class_type.__module__ == builtins.__name__


def get_class_parameter_type_hints(obj: Union[Callable, Type]) -> Dict[str, Any]:
    """Returns a mapping of parameter names and their corresponding type hint
    for classes which are not part of the builtins.
    """
    params: ItemsView[str, Parameter] = inspect.signature(obj).parameters.items()

    return {k: v.annotation for k, v in params if not (v.annotation is v.empty or is_builtin_class(v.annotation))}


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
