from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, TypeVar

from wireup._discovery import register_services_from_modules
from wireup.errors import UnknownParameterError
from wireup.ioc.container.async_container import AsyncContainer
from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.container.sync_container import SyncContainer
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.service_registry import ServiceRegistry
from wireup.ioc.types import ContainerScope, ParameterWrapper

if TYPE_CHECKING:
    from types import ModuleType

_ContainerT = TypeVar("_ContainerT", bound=BaseContainer)


def _create_container(
    klass: type[_ContainerT],
    *,
    service_modules: list[ModuleType] | None = None,
    parameters: dict[str, Any] | None = None,
) -> _ContainerT:
    """Create a Wireup container.

    :param service_modules: This is a list of top-level modules containing services registered
    with `@service` or `@abstract`. Wireup will recursively scan the modules and register services found in them.
    :param parameters: Dict containing parameters you want to expose to the container. Services or factories can
    request parameters via the `Inject(param="name")` syntax.
    """
    container = klass(
        registry=ServiceRegistry(),
        parameters=ParameterBag(parameters),
        global_scope=ContainerScope(),
        overrides={},
    )
    if service_modules:
        register_services_from_modules(container._registry, service_modules)

    _assert_dependencies_valid(container)

    return container


def _assert_dependencies_valid(container: BaseContainer) -> None:
    for target, dependencies in container._registry.context.dependencies.items():
        for name, annotated_parameter in dependencies.items():
            if isinstance(annotated_parameter.annotation, ParameterWrapper):
                try:
                    container.params.get(annotated_parameter.annotation.param)
                except UnknownParameterError as e:
                    msg = (
                        f"Service {target}.{name} depends on an unknown "
                        f"parameter {annotated_parameter.annotation.param}."
                    )
                    raise ValueError(msg) from e
            elif not container._registry.is_type_with_qualifier_known(
                annotated_parameter.klass, qualifier=annotated_parameter.qualifier_value
            ):
                msg = (
                    f"Service {target}.{name} depends on an unknown service {annotated_parameter.klass} "
                    f"with qualifier {annotated_parameter.qualifier_value}."
                )
                raise ValueError(msg)


create_sync_container = functools.partial(_create_container, SyncContainer)
create_async_container = functools.partial(_create_container, AsyncContainer)
