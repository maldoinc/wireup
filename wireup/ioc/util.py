from __future__ import annotations

import fnmatch
import pkgutil
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from types import ModuleType


def find_classes_in_module(module: ModuleType, pattern: str = "*") -> Generator[type, None, None]:
    for _, modname, __ in pkgutil.walk_packages(module.__path__, prefix=module.__name__ + "."):
        mod = __import__(modname, fromlist="dummy")

        for name in dir(mod):
            obj = getattr(mod, name)

            if isinstance(obj, type) and obj.__module__ == mod.__name__ and fnmatch.fnmatch(obj.__name__, pattern):
                yield obj
