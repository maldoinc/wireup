from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, TypeVar

from wireup._annotations import AbstractDeclaration, ServiceDeclaration
from wireup._discovery import discover_wireup_registrations
from wireup.errors import WireupError
from wireup.ioc.container.async_container import AsyncContainer
from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.container.compiler import FactoryCompiler
from wireup.ioc.container.sync_container import SyncContainer
from wireup.ioc.override_manager import OverrideManager
from wireup.ioc.parameter import ParameterBag
from wireup.ioc.service_registry import ServiceRegistry
from wireup.ioc.types import ContainerScope

if TYPE_CHECKING:
    from types import ModuleType

_ContainerT = TypeVar("_ContainerT", bound=BaseContainer)


def _create_container(
    klass: type[_ContainerT],
    *,
    service_modules: Iterable[ModuleType] | None = None,
    services: Iterable[Any] | None = None,
    parameters: dict[str, Any] | None = None,
) -> _ContainerT:
    """Create a Wireup container.

    :param service_modules: This is a list of top-level modules containing services registered
    with `@service` or `@abstract`. Wireup will recursively scan the modules and register services found in them.
    :param services: A list of classes or functions decorated with `@service` or `@abstract` to register with the
    container instance. Use this when you want to explicitly list services.
    :param parameters: Dict containing parameters you want to expose to the container. Services or factories can
    request parameters via the `Inject(param="name")` syntax.
    """
    abstracts: list[AbstractDeclaration] = []
    impls: list[ServiceDeclaration] = []

    if services:
        for service in services:
            if not hasattr(service, "__wireup_registration__"):
                msg = f"Service {service} is not decorated with @abstract or @service."
                raise WireupError(msg)

            reg: AbstractDeclaration | ServiceDeclaration = service.__wireup_registration__

            if isinstance(reg, AbstractDeclaration):
                abstracts.append(reg)
            else:
                impls.append(reg)

    if service_modules:
        discovered_abstracts, discovered_services = discover_wireup_registrations(service_modules)
        abstracts.extend(discovered_abstracts)
        impls.extend(discovered_services)

    registry = ServiceRegistry(parameters=ParameterBag(parameters), abstracts=abstracts, impls=impls)
    compiler = FactoryCompiler(registry, is_scoped_container=False)
    scoped_compiler = FactoryCompiler(registry, is_scoped_container=True)
    override_manager = OverrideManager(registry.is_type_with_qualifier_known, compiler, scoped_compiler)
    container = klass(
        registry=registry,
        factory_compiler=compiler,
        scoped_compiler=scoped_compiler,
        global_scope=ContainerScope(objects={}, exit_stack=[]),
        override_manager=override_manager,
    )

    compiler.compile()
    scoped_compiler.compile()

    return container


def create_sync_container(
    service_modules: list[ModuleType] | None = None,
    services: list[Any] | None = None,
    parameters: dict[str, Any] | None = None,
) -> SyncContainer:
    """Create a Wireup container.

    :param service_modules: This is a list of top-level modules containing services registered
    with `@service` or `@abstract`. Wireup will recursively scan the modules and register services found in them.
    :param services: A list of classes or functions decorated with `@service` or `@abstract` to register with the
    container instance. Use this when you want to explicitly list services.
    :param parameters: Dict containing parameters you want to expose to the container. Services or factories can
    request parameters via the `Inject(param="name")` syntax.
    :raises WireupError: Raised if the dependencies cannot be fully resolved.
    """
    return _create_container(SyncContainer, service_modules=service_modules, services=services, parameters=parameters)


def create_async_container(
    service_modules: list[ModuleType] | None = None,
    services: list[Any] | None = None,
    parameters: dict[str, Any] | None = None,
) -> AsyncContainer:
    """Create a Wireup container.

    :param service_modules: This is a list of top-level modules containing services registered
    with `@service` or `@abstract`. Wireup will recursively scan the modules and register services found in them.
    :param services: A list of classes or functions decorated with `@service` or `@abstract` to register with the
    container instance. Use this when you want to explicitly list services.
    :param parameters: Dict containing parameters you want to expose to the container. Services or factories can
    request parameters via the `Inject(param="name")` syntax.
    :raises WireupError: Raised if the dependencies cannot be fully resolved.
    """
    return _create_container(AsyncContainer, service_modules=service_modules, services=services, parameters=parameters)
