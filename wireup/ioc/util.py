from __future__ import annotations

import fnmatch
import pkgutil
from dataclasses import dataclass
from inspect import Parameter
from typing import TYPE_CHECKING, Any, Generator, TypeVar

if TYPE_CHECKING:
    from types import ModuleType

T = TypeVar("T")


def find_classes_in_module(module: ModuleType, pattern: str = "*") -> Generator[type[T], None, None]:
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


@dataclass
class AnnotatedParameter:
    """Represents a function parameter with a single optional annotation."""

    klass: type[T] | None
    annotation: Any | None


def parameter_get_type_and_annotation(parameter: Parameter) -> AnnotatedParameter:
    """Get the annotation injection type from a signature's Parameter.

    Returns either the first annotation for an Annotated type or the default value.
    """
    annotated_type = None if parameter.annotation is Parameter.empty else parameter.annotation

    if hasattr(annotated_type, "__metadata__") and hasattr(annotated_type, "__args__"):
        return AnnotatedParameter(klass=annotated_type.__args__[0], annotation=annotated_type.__metadata__[0])

    return AnnotatedParameter(annotated_type, None if parameter.default is Parameter.empty else parameter.default)
