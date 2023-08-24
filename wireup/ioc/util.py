from __future__ import annotations

import fnmatch
import pkgutil
from typing import TYPE_CHECKING, Generator, TypeVar

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
