from __future__ import annotations

import fnmatch
import importlib
import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import ModuleType

    from wireup import DependencyContainer


def warmup_container(dependency_container: DependencyContainer, service_modules: list[ModuleType]) -> None:
    """Import all modules provided in `service_modules` and initializes all registered singleton services.

    !!! note
        For long-lived processes this should be executed once at startup.
    """
    for module in service_modules:
        for _ in _find_classes_in_module(module):
            pass

    dependency_container.warmup()


def _find_classes_in_module(module: ModuleType, pattern: str = "*") -> list[type]:
    classes = []

    def _module_get_classes(m: ModuleType) -> list[type]:
        return [
            klass
            for name, klass in inspect.getmembers(m)
            if isinstance(klass, type) and klass.__module__.startswith(m.__name__) and fnmatch.fnmatch(name, pattern)
        ]

    def _find_in_path(path: Path, parent_module_name: str) -> None:
        for file in path.iterdir():
            full_path = path / file

            if Path.is_dir(full_path):
                sub_module_name = f"{parent_module_name}.{file.name}"
                _find_in_path(full_path, sub_module_name)
            elif file.name.endswith(".py"):
                full_module_name = f"{parent_module_name}.{file.name[:-3]}"
                sub_module = importlib.import_module(full_module_name)
                classes.extend(_module_get_classes(sub_module))

    if f := module.__file__:
        _find_in_path(Path(f).parent, module.__name__)

    return classes


def register_all_in_module(container: DependencyContainer, module: ModuleType, pattern: str = "*") -> None:
    """Register all modules inside a given module.

    Useful when your services reside in one place, and you'd like to avoid having to `@container.register` each of them.
    Alternatively this can be used if you want to use the library without having to rely on decorators.

    See Also: `DependencyContainer.context` to manually wire dependencies without having to use annotations.

    :param container: Dependency container to register services in.
    :param module: The package name to recursively search for classes.
    :param pattern: A pattern that will be fed to fnmatch to determine if a class will be registered or not.
    """
    klass: type[Any]
    for klass in _find_classes_in_module(module, pattern):
        container.register(klass)
