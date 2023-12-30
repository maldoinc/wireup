from wireup.annotation import ParameterEnum, Wire, wire
from wireup.import_util import register_all_in_module, warmup_container
from wireup.ioc.dependency_container import DependencyContainer
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.types import ParameterReference, ServiceLifetime, ServiceOverride

container = DependencyContainer(ParameterBag())
"""Singleton DI container instance.

Use when your application only needs one container.
"""


__all__ = [
    "DependencyContainer",
    "ParameterBag",
    "ParameterEnum",
    "ParameterReference",
    "ServiceLifetime",
    "ServiceOverride",
    "Wire",
    "container",
    "register_all_in_module",
    "warmup_container",
    "wire",
]
