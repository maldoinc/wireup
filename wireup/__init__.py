from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wireup.annotation import ParameterEnum, Wire, wire
from wireup.ioc.dependency_container import DependencyContainer
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.types import ParameterReference, ServiceLifetime
from wireup.ioc.util import import_all_in_module

if TYPE_CHECKING:
    from types import ModuleType

container: DependencyContainer[Any] = DependencyContainer(ParameterBag())
"""Singleton DI container instance.

Use when your application only needs one container.
"""


def optimize_container(dependency_container: DependencyContainer[Any], service_modules: list[ModuleType]) -> None:
    """Import all modules provided in `service_modules` and initializes all registered singleton services.

    !!! note
        For long-lived processes this should be executed once at startup.
    """
    for module in service_modules:
        import_all_in_module(module)

    dependency_container.optimize()


__all__ = [
    "DependencyContainer",
    "ParameterBag",
    "ParameterEnum",
    "ParameterReference",
    "ServiceLifetime",
    "Wire",
    "container",
    "wire",
]
