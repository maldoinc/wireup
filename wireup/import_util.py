from __future__ import annotations

import fnmatch
import importlib
import pkgutil
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import ModuleType

    from wireup import DependencyContainer


__T = TypeVar("__T")


def _import_all_in_module(module: ModuleType) -> None:
    """Recursively load all modules and submodules within a given module."""
    for _, module_name, _ in pkgutil.walk_packages(module.__path__):
        importlib.import_module(f"{module.__name__}.{module_name}")


def warmup_container(dependency_container: DependencyContainer[Any], service_modules: list[ModuleType]) -> None:
    """Import all modules provided in `service_modules` and initializes all registered singleton services.

    !!! note
        For long-lived processes this should be executed once at startup.
    """
    for module in service_modules:
        _import_all_in_module(module)

    dependency_container.warmup()


def _find_classes_in_module(module: ModuleType, pattern: str = "*") -> Generator[type[__T], None, None]:
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


def register_all_in_module(container: DependencyContainer[Any], module: ModuleType, pattern: str = "*") -> None:
    """Register all modules inside a given module.

    Useful when your components reside in one place, and you'd like to avoid having to `@register` each of them.
    Alternatively this can be used if you want to use the library without having to rely on decorators.

    See Also: `self.initialization_context` to wire parameters without having to use a default value.

    :param container: Dependency container to register services in.
    :param module: The package name to recursively search for classes.
    :param pattern: A pattern that will be fed to fnmatch to determine if a class will be registered or not.
    """
    klass: type[Any]
    for klass in _find_classes_in_module(module, pattern):
        container.register(klass)
