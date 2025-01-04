import warnings

from wireup.annotation import Inject, ParameterEnum, Wire, abstract, service, wire
from wireup.ioc.dependency_container import DependencyContainer
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.types import ParameterReference, ServiceLifetime, ServiceOverride
from wireup.util import (
    create_container,
    initialize_container,
    load_module,
    register_all_in_module,
    warmup_container,
)

_deprecated_container = DependencyContainer(ParameterBag())
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
    "create_container",
    "initialize_container",
    "load_module",
    "register_all_in_module",
    "service",
    "warmup_container",
    "wire",
]


def __getattr__(name: str) -> DependencyContainer:
    if name == "container":
        warnings.warn(
            "Using the wireup.container singleton is deprecated. "
            "Create your own instance of the container using wireup.create_container. "
            "See: https://maldoinc.github.io/wireup/latest/getting_started/",
            DeprecationWarning,
            stacklevel=2,
        )
        return _deprecated_container

    msg = f"module {__name__} has no attribute {name}"
    raise AttributeError(msg)
