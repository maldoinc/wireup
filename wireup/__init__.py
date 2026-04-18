from __future__ import annotations

from wireup._annotations import Inject, Injected, abstract, injectable, service
from wireup._decorators import inject_from_container
from wireup._instance import instance
from wireup.ioc.container import (
    create_async_container,
    create_sync_container,
)
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer
from wireup.ioc.container.sync_container import ScopedSyncContainer, SyncContainer
from wireup.ioc.types import InjectableOverride
from wireup.ioc.types import InjectableOverride as ServiceOverride
from wireup.util import qualified

__all__ = [
    "AsyncContainer",
    "Inject",
    "InjectableOverride",
    "Injected",
    "ScopedAsyncContainer",
    "ScopedSyncContainer",
    "ServiceOverride",
    "SyncContainer",
    "abstract",
    "create_async_container",
    "create_sync_container",
    "inject_from_container",
    "injectable",
    "instance",
    "qualified",
    "service",
]
