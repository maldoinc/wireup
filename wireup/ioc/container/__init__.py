from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, TypeVar

from wireup._annotations import AbstractDeclaration, ServiceDeclaration
from wireup._discovery import discover_wireup_registrations
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

    _assert_dependencies_valid(container)

    return container


def _assert_dependencies_valid(container: BaseContainer) -> None:
    """Assert that all required dependencies exist for this container instance."""
    for (impl, _), service_factory in container._registry.factories.items():
        for name, dependency in container._registry.dependencies[service_factory.factory].items():
            assert_dependency_exists(container=container, parameter=dependency, target=impl, name=name)

            if (
                not dependency.is_parameter
                and container._registry.lifetime[impl] == "singleton"
                and (dep_lifetime := container._registry.lifetime[dependency.klass]) != "singleton"
            ):
                msg = (
                    f"Parameter '{name}' of {type(impl).__name__.capitalize()} {impl.__module__}.{impl.__name__} "
                    f"depends on a service with a '{dep_lifetime}' lifetime which is not supported. "
                    "Singletons can only depend on other singletons."
                )
                raise WireupError(msg)


def assert_dependency_exists(container: BaseContainer, parameter: AnnotatedParameter, target: Any, name: str) -> None:
    """Assert that a dependency exists in the container for the given annotated parameter."""
    if isinstance(parameter.annotation, ParameterWrapper):
        try:
            container.params.get(parameter.annotation.param)
        except UnknownParameterError as e:
            msg = (
                f"Parameter '{name}' of {_get_fqcn(target)} "
                f"depends on an unknown Wireup parameter '{e.parameter_name}'"
                + (
                    ""
                    if isinstance(parameter.annotation.param, str)
                    else f" requested in expression '{parameter.annotation.param.value}'"
                )
                + "."
            )
            raise WireupError(msg) from e
    elif not container._registry.is_type_with_qualifier_known(parameter.klass, qualifier=parameter.qualifier_value):
        msg = (
            f"Parameter '{name}' of {_get_fqcn(target)} "
            f"depends on an unknown service {_get_fqcn(parameter.klass)} with qualifier {parameter.qualifier_value}."
        )
        raise WireupError(msg)


def _get_fqcn(target: type) -> str:
    return f"{type(target).__name__.capitalize()} {target.__module__}.{target.__name__}"


create_sync_container = functools.partial(_create_container, SyncContainer)
create_async_container = functools.partial(_create_container, AsyncContainer)
