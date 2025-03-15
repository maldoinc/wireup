from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, TypeVar

from wireup._discovery import register_services_from_modules
from wireup.errors import UnknownParameterError, WireupError
from wireup.ioc.container.async_container import AsyncContainer
from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.container.sync_container import SyncContainer
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.service_registry import ServiceRegistry
from wireup.ioc.types import AnnotatedParameter, ContainerScope, ParameterWrapper

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
            assert_dependency_exists(container=container, parameter=annotated_parameter, target=target, name=name)


def assert_dependency_exists(container: BaseContainer, parameter: AnnotatedParameter, target: Any, name: str) -> None:
    """Assert that a dependency exists in the container for the given annotated parameter."""
    if isinstance(parameter.annotation, ParameterWrapper):
        try:
            container.params.get(parameter.annotation.param)
        except UnknownParameterError as e:
            msg = (
                f"Parameter '{name}' of {type(target).__name__.capitalize()} {target.__module__}.{target.__name__} "
                f"depends on an unknown Wireup parameter '{parameter.annotation.param}'."
            )
            raise WireupError(msg) from e
    elif not container._registry.is_type_with_qualifier_known(parameter.klass, qualifier=parameter.qualifier_value):
        msg = (
            f"Parameter '{name}' of {type(target).__name__.capitalize()} {target.__module__}.{target.__name__} "
            f"depends on an unknown service {parameter.klass} with qualifier {parameter.qualifier_value}."
        )
        raise WireupError(msg)


create_sync_container = functools.partial(_create_container, SyncContainer)
create_async_container = functools.partial(_create_container, AsyncContainer)
