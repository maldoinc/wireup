from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from types import FunctionType, ModuleType
from typing import TYPE_CHECKING, Any, Callable

from wireup.annotation import AbstractDeclaration, ServiceDeclaration

if TYPE_CHECKING:
    from wireup.ioc.service_registry import ServiceRegistry


def register_services_from_modules(registry: ServiceRegistry, service_modules: list[ModuleType]) -> None:
    abstract_registrations: set[type[Any]] = set()
    service_registrations: list[ServiceDeclaration] = []

    def _is_valid_wireup_target(obj: Any) -> bool:
        # Check that the hasattr call is only made on user defined functions and classes.
        # This is so that it avoids interacting with proxies and things such as flask.g when imported.
        # "from flask import g" would cause a hasattr call to g outside of app context.
        return (isinstance(obj, FunctionType) or inspect.isclass(obj)) and hasattr(obj, "__wireup_registration__")

    for module in service_modules:
        for cls in _find_objects_in_module(module, predicate=_is_valid_wireup_target):
            reg = getattr(cls, "__wireup_registration__", None)

            if isinstance(reg, ServiceDeclaration):
                service_registrations.append(reg)
            elif isinstance(reg, AbstractDeclaration):
                abstract_registrations.add(cls)

    for cls in abstract_registrations:
        registry.register_abstract(cls)

    for svc in service_registrations:
        if isinstance(svc.obj, type) or callable(svc.obj):
            registry.register(obj=svc.obj, qualifier=svc.qualifier, lifetime=svc.lifetime)


def _find_objects_in_module(module: ModuleType, predicate: Callable[[Any], bool]) -> set[type]:
    classes: set[type[Any]] = set()

    def _module_get_objects(m: ModuleType) -> set[type]:
        return {obj for _, obj in inspect.getmembers(m) if predicate(obj)}

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
        if f.endswith("__init__.py"):
            _find_in_path(Path(f).parent, module.__name__)
        else:
            classes.update(_module_get_objects(module))

    return classes
