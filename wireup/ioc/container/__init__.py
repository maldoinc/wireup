from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, TypeVar

from wireup._annotations import AbstractDeclaration, ServiceDeclaration
from wireup._discovery import discover_wireup_registrations
from wireup.ioc.container.async_container import AsyncContainer
from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.container.sync_container import SyncContainer
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.service_registry import ServiceRegistry
from wireup.ioc.types import ContainerScope
from wireup.ioc.validation import assert_dependencies_valid

if TYPE_CHECKING:
    from types import ModuleType

_ContainerT = TypeVar("_ContainerT", bound=BaseContainer)


def _create_container(
    klass: type[_ContainerT],
    *,
    service_modules: list[ModuleType] | None = None,
    services: list[Any] | None = None,
    parameters: dict[str, Any] | None = None,
) -> _ContainerT:
    """Create a Wireup container.

    :param service_modules: This is a list of top-level modules containing services registered
    with `@service` or `@abstract`. Wireup will recursively scan the modules and register services found in them.
    :param parameters: Dict containing parameters you want to expose to the container. Services or factories can
    request parameters via the `Inject(param="name")` syntax.
    """
    abstracts: list[AbstractDeclaration] = []
    impls: list[ServiceDeclaration] = []

    if services:
        for service in services:
            if not hasattr(service, "__wireup_registration__"):
                msg = f"Service {service} is not decorated with @abstract or @service."
                raise ValueError(msg)

            reg: AbstractDeclaration | ServiceDeclaration = service.__wireup_registration__

            if isinstance(reg, AbstractDeclaration):
                abstracts.append(reg)
            else:
                impls.append(reg)

    if service_modules:
        discovered_abstracts, discovered_services = discover_wireup_registrations(service_modules)
        abstracts.extend(discovered_abstracts)
        impls.extend(discovered_services)

    container = klass(
        registry=ServiceRegistry(),
        parameters=ParameterBag(parameters),
        global_scope=ContainerScope(),
        overrides={},
    )

    for abstract in abstracts:
        container._registry.register_abstract(abstract.obj)

    for impl in impls:
        container._registry.register(obj=impl.obj, lifetime=impl.lifetime, qualifier=impl.qualifier)

    assert_dependencies_valid(container)

    return container


create_sync_container = functools.partial(_create_container, SyncContainer)
create_async_container = functools.partial(_create_container, AsyncContainer)
