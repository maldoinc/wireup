from __future__ import annotations

import fnmatch
import importlib
import inspect
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wireup.annotation import AbstractDeclaration, ServiceDeclaration

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from wireup import DependencyContainer


def initialize_container(dependency_container: DependencyContainer, *, service_modules: list[ModuleType]) -> None:
    """Trigger service registrations in `service_modules` and initialize registered singleton services.

    !!! note
        For long-lived processes this should be executed once at startup.
    """
    _register_services(dependency_container, service_modules)
    dependency_container.warmup()


def warmup_container(dependency_container: DependencyContainer, service_modules: list[ModuleType]) -> None:
    """Trigger service registrations in `service_modules` and initialize registered singleton services.

    !!! note
        For long-lived processes this should be executed once at startup.
    """
    warnings.warn(
        "Using warmup_container is deprecated. Use 'initialize_container' instead",
        stacklevel=2,
    )
    initialize_container(dependency_container, service_modules=service_modules)


def _register_services(dependency_container: DependencyContainer, service_modules: list[ModuleType]) -> None:
    abstract_registrations: set[type[Any]] = set()
    service_registrations: list[ServiceDeclaration] = []

    for module in service_modules:
        for cls in _find_objects_in_module(module, predicate=lambda obj: hasattr(obj, "__wireup_registration__")):
            reg = getattr(cls, "__wireup_registration__", None)

            if isinstance(reg, ServiceDeclaration):
                service_registrations.append(reg)
            elif isinstance(reg, AbstractDeclaration):
                abstract_registrations.add(cls)

    for cls in abstract_registrations:
        dependency_container.abstract(cls)

    for svc in service_registrations:
        dependency_container.register(obj=svc.obj, qualifier=svc.qualifier, lifetime=svc.lifetime)


def _find_objects_in_module(
    module: ModuleType, predicate: Callable[[Any], bool], pattern: str | re.Pattern[str] = "*"
) -> set[type]:
    classes: set[type[Any]] = set()

    def _module_get_objects(m: ModuleType) -> set[type]:
        return {
            obj
            for name, obj in inspect.getmembers(m)
            if predicate(obj)
            and obj.__module__.startswith(m.__name__)
            and (fnmatch.fnmatch(name, pattern) if isinstance(pattern, str) else re.match(pattern, name))
        }

    def _find_in_path(path: Path, parent_module_name: str) -> None:
        for file in path.iterdir():
            if file.name == "__pycache__":
                continue

            full_path = path / file

            if Path.is_dir(full_path):
                sub_module_name = f"{parent_module_name}.{file.name}"
                _find_in_path(full_path, sub_module_name)
            elif file.name.endswith(".py"):
                full_module_name = (
                    parent_module_name if file.name == "__init__.py" else f"{parent_module_name}.{file.name[:-3]}"
                )
                sub_module = importlib.import_module(full_module_name)
                classes.update(_module_get_objects(sub_module))

    if f := module.__file__:
        _find_in_path(Path(f).parent, module.__name__)

    return classes


def register_all_in_module(
    container: DependencyContainer, module: ModuleType, pattern: str | re.Pattern[str] = "*"
) -> None:
    """Register all modules inside a given module.

    Useful when your services reside in one place, and you'd like to avoid having to `@container.register` each of them.
    Alternatively this can be used if you want to use the library without having to rely on decorators.

    See Also: `DependencyContainer.context` to manually wire dependencies without having to use annotations.

    :param container: Dependency container to register services in.
    :param module: The package name to recursively search for classes.
    :param pattern: A string representing a fnmatch pattern or a regular expression compiled with re.compile.
    """
    warnings.warn(
        "Using register_all_in_module is deprecated. "
        "Use @service or factories in conjunction with initialize_container to register services.",
        stacklevel=2,
    )
    klass: type[Any]
    for klass in _find_objects_in_module(module, predicate=lambda obj: isinstance(obj, type), pattern=pattern):
        container.register(klass)


def load_module(module: ModuleType) -> None:
    """Recursively load a given module.

    This can be useful to import them module and trigger any container registrations.
    """
    warnings.warn(
        "Using load_module is deprecated. "
        "Use @service or factories in conjunction with initialize_container to register services.",
        stacklevel=2,
    )
    _find_objects_in_module(module, lambda _: True)
