from __future__ import annotations

import fnmatch
import functools
import importlib
import inspect
import re
import types
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from wireup.annotation import AbstractDeclaration, ServiceDeclaration
from wireup.ioc.async_container import AsyncContainer
from wireup.ioc.base_container import BaseContainer
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.service_registry import ServiceRegistry
from wireup.ioc.sync_container import SyncContainer
from wireup.ioc.types import ContainerScope

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

_ContainerT = TypeVar("_ContainerT", bound=BaseContainer)


def _create_container(
    klass: type[_ContainerT],
    *,
    service_modules: list[ModuleType] | None = None,
    parameters: dict[str, Any] | None = None,
) -> _ContainerT:
    """Create a container with the given parameters and register all services found in service modules."""
    bag = ParameterBag()
    registry = ServiceRegistry()
    if parameters:
        bag.update(parameters)
    container = klass(
        registry=registry,
        parameters=bag,
        global_scope=ContainerScope(),
        overrides={},
    )
    if service_modules:
        _register_services(registry, service_modules)

    return container


create_sync_container = functools.partial(_create_container, SyncContainer)
create_async_container = functools.partial(_create_container, AsyncContainer)


def _register_services(registry: ServiceRegistry, service_modules: list[ModuleType]) -> None:
    abstract_registrations: set[type[Any]] = set()
    service_registrations: list[ServiceDeclaration] = []

    def _is_valid_wireup_target(obj: Any) -> bool:
        # Check that the hasattr call is only made on user defined functions and classes.
        # This is so that it avoids interacting with proxies and things such as flask.g when imported.
        # "from flask import g" would cause a hasattr call to g outside of app context.
        return (isinstance(obj, types.FunctionType) or inspect.isclass(obj)) and hasattr(obj, "__wireup_registration__")

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
        if isinstance(svc.obj, type):
            registry.register_service(klass=svc.obj, qualifier=svc.qualifier, lifetime=svc.lifetime)
        elif callable(svc.obj):
            registry.register_factory(fn=svc.obj, qualifier=svc.qualifier, lifetime=svc.lifetime)


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
        if f.endswith("__init__.py"):
            _find_in_path(Path(f).parent, module.__name__)
        else:
            classes.update(_module_get_objects(module))

    return classes
