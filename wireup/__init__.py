from wireup.annotation import Inject, ParameterEnum, Wire, abstract, service, wire
from wireup.import_util import initialize_container, load_module, register_all_in_module, warmup_container
from wireup.ioc.dependency_container import DependencyContainer
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.types import ParameterReference, ServiceLifetime, ServiceOverride

container = DependencyContainer(ParameterBag())
"""Singleton DI container instance.

Use when your application only needs one container.
"""

__all__ = [
    "DependencyContainer",
    "Inject",
    "ParameterBag",
    "ParameterEnum",
    "ParameterReference",
    "ServiceLifetime",
    "ServiceOverride",
    "Wire",
    "abstract",
    "container",
    "load_module",
    "register_all_in_module",
    "service",
    "warmup_container",
    "initialize_container",
    "wire",
]
