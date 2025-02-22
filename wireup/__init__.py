import warnings

from wireup.annotation import Inject, abstract, service
from wireup.ioc.async_container import AsyncContainer
from wireup.ioc.dependency_container import DependencyContainer
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.scoped_container import ScopedContainer, enter_async_scope, enter_scope
from wireup.ioc.sync_container import SyncContainer
from wireup.ioc.types import ParameterReference, ServiceLifetime, ServiceOverride
from wireup.util import (
    create_async_container,
    create_container,
    create_sync_container,
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
    "AsyncContainer",
    "DependencyContainer",
    "Inject",
    "ParameterBag",
    "ParameterReference",
    "ScopedContainer",
    "ServiceLifetime",
    "ServiceOverride",
    "SyncContainer",
    "abstract",
    "create_async_container",
    "create_container",
    "create_sync_container",
    "enter_async_scope",
    "enter_scope",
    "initialize_container",
    "load_module",
    "register_all_in_module",
    "service",
    "warmup_container",
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
