from __future__ import annotations

import importlib
import pkgutil
import typing
from inspect import Parameter
from typing import TYPE_CHECKING, Any, TypeVar

from wireup.ioc.types import AnnotatedParameter

if TYPE_CHECKING:
    from types import ModuleType

__T = TypeVar("__T")


def parameter_get_type_and_annotation(parameter: Parameter) -> AnnotatedParameter[__T]:
    """Get the annotation injection type from a signature's Parameter.

    Returns either the first annotation for an Annotated type or the default value.
    """
    if hasattr(parameter.annotation, "__metadata__") and hasattr(parameter.annotation, "__args__"):
        klass = parameter.annotation.__args__[0]
        annotation = parameter.annotation.__metadata__[0]
    else:
        klass = None if parameter.annotation is Parameter.empty else parameter.annotation
        annotation = None if parameter.default is Parameter.empty else parameter.default

    return AnnotatedParameter(klass=klass, annotation=annotation)


def is_type_autowireable(obj_type: Any) -> bool:
    """Determine if the given type is can be autowired without additional annotations."""
    if obj_type is None or obj_type in {int, float, str, bool, complex, bytes, bytearray, memoryview}:
        return False

    return not (hasattr(obj_type, "__origin__") and obj_type.__origin__ == typing.Union)


def import_all_in_module(module: ModuleType) -> None:
    """Recursively load all modules and submodules within a given module."""
    for _, module_name, _ in pkgutil.walk_packages(module.__path__):
        importlib.import_module(f"{module.__name__}.{module_name}")
