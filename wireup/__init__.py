import warnings

from wireup._annotations import Inject, Injected, abstract, injectable, service
from wireup._decorators import inject_from_container
from wireup.ioc.container import (
    create_async_container,
    create_sync_container,
)
from wireup.ioc.container.async_container import AsyncContainer
from wireup.ioc.container.sync_container import SyncContainer
from wireup.ioc.types import ConfigurationReference, InjectableOverride

__all__ = [
    "AsyncContainer",
    "ConfigurationReference",
    "Inject",
    "InjectableOverride",
    "Injected",
    "ServiceOverride",
    "SyncContainer",
    "abstract",
    "create_async_container",
    "create_sync_container",
    "inject_from_container",
    "injectable",
    "service",
]


def __getattr__(name: str) -> object:
    if name == "ServiceOverride":
        warnings.warn(
            "ServiceOverride is deprecated. Use InjectableOverride instead.",
            FutureWarning,
            stacklevel=2,
        )
        return InjectableOverride
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
