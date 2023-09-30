from __future__ import annotations

import fnmatch
import pkgutil
import typing
from dataclasses import dataclass
from inspect import Parameter
from typing import TYPE_CHECKING, Any, Generator, Generic, TypeVar

if TYPE_CHECKING:
    from types import ModuleType

__T = TypeVar("__T")


def find_classes_in_module(module: ModuleType, pattern: str = "*") -> Generator[type[__T], None, None]:
    """Return a list of object types found in a given module that matches the pattern in the argument.

    :param module: The module under which to recursively look for types.
    :param pattern: A fnmatch pattern which the type name will be tested against.
    """
    for _, modname, __ in pkgutil.walk_packages(module.__path__, prefix=module.__name__ + "."):
        mod = __import__(modname, fromlist="dummy")

        for name in dir(mod):
            obj = getattr(mod, name)

            if isinstance(obj, type) and obj.__module__ == mod.__name__ and fnmatch.fnmatch(obj.__name__, pattern):
                yield obj


@dataclass(frozen=True, eq=True)
class AnnotatedParameter(Generic[__T]):
    """Represents a function parameter with a single optional annotation."""

    klass: type[__T] | None = None
    annotation: Any | None = None


def parameter_get_type_and_annotation(parameter: Parameter) -> AnnotatedParameter[__T]:
    """Get the annotation injection type from a signature's Parameter.

    Returns either the first annotation for an Annotated type or the default value.
    """
    if hasattr(parameter.annotation, "__metadata__") and hasattr(parameter.annotation, "__args__"):
        return AnnotatedParameter(
            klass=parameter.annotation.__args__[0],
            annotation=parameter.annotation.__metadata__[0],
        )

    return AnnotatedParameter(
        None if parameter.annotation is Parameter.empty else parameter.annotation,
        None if parameter.default is Parameter.empty else parameter.default,
    )


def is_type_autowireable(obj_type: Any) -> bool:
    """Determine if the given type is can be autowired without additional annotations."""
    if obj_type in {int, float, str, bool, complex, bytes, bytearray, memoryview}:
        return False

    return not (hasattr(obj_type, "__origin__") and obj_type.__origin__ == typing.Union)
