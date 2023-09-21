from __future__ import annotations

from wireup.annotation import ParameterEnum, Wire, wire
from wireup.ioc.container_util import ParameterReference, ServiceLifetime
from wireup.ioc.dependency_container import DependencyContainer
from wireup.ioc.parameter import ParameterBag

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
    "Wire",
    "container",
    "wire",
]
