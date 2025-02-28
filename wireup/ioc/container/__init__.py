from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, TypeVar

from wireup._discovery import register_services_from_modules
from wireup.ioc.container.async_container import AsyncContainer
from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.container.sync_container import SyncContainer
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.service_registry import ServiceRegistry
from wireup.ioc.types import ContainerScope

if TYPE_CHECKING:
    from types import ModuleType

_ContainerT = TypeVar("_ContainerT", bound=BaseContainer)


def _create_container(
    klass: type[_ContainerT],
    *,
    service_modules: list[ModuleType] | None = None,
    parameters: dict[str, Any] | None = None,
) -> _ContainerT:
    """Create a container with the given parameters and register all services found in service modules."""
    container = klass(
        registry=ServiceRegistry(),
        parameters=ParameterBag(parameters),
        global_scope=ContainerScope(),
        overrides={},
    )
    if service_modules:
        register_services_from_modules(container._registry, service_modules)

    return container


create_sync_container = functools.partial(_create_container, SyncContainer)
create_async_container = functools.partial(_create_container, AsyncContainer)
