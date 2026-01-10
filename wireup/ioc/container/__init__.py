from __future__ import annotations

import warnings
from types import ModuleType
from typing import Any, Iterable, TypeVar

from wireup._annotations import AbstractDeclaration, InjectableDeclaration
from wireup._discovery import discover_wireup_registrations
from wireup.errors import WireupError
from wireup.ioc.configuration import ConfigStore
from wireup.ioc.container.async_container import AsyncContainer
from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.container.sync_container import SyncContainer
from wireup.ioc.factory_compiler import FactoryCompiler
from wireup.ioc.override_manager import OverrideManager
from wireup.ioc.registry import ContainerRegistry

_ContainerT = TypeVar("_ContainerT", bound=BaseContainer)


def _create_container(  # noqa: PLR0913
    klass: type[_ContainerT],
    *,
    service_modules: Iterable[ModuleType] | None = None,
    services: Iterable[Any] | None = None,
    parameters: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    injectables: list[Any] | None = None,
) -> _ContainerT:
    """Create a Wireup container.

    :param service_modules: Deprecated: Use injectables instead.
        This is a list of top-level modules containing services registered
        with `@injectable` or `@abstract`. Wireup will recursively scan the modules and register services found in them.
    :param services: Deprecated: Use injectables instead.
        A list of classes or functions decorated with `@injectable` or `@abstract` to register with the
        container instance. Use this when you want to explicitly list services.
    :param parameters: Deprecated. Parameters was renamed to config, use that instead.
    :param config: Configuration to expose to the container. Injectables or factories can
        request config via the `Inject(config="name")` annotation.
    :param injectables: A list of classes or functions decorated with `@injectable` or `@abstract` or modules containing
        injectables to register with the container instance.
    :raises WireupError: Raised if the dependencies cannot be fully resolved.
    """

    if parameters is not None:
        msg = "Parameters have been renamed to Config. Pass your configuration to the config parameter."
        warnings.warn(msg, FutureWarning, stacklevel=2)

        if config is not None:
            msg = (
                "Passing both 'parameters' and 'config' is not supported. "
                "Please use only 'config' as 'parameters' is deprecated."
            )
            raise WireupError(msg)

    if services or service_modules:
        msg = (
            "Services have been renamed to Injectables. Pass your injectables or modules containing injectables  "
            "to the injectables."
        )
        warnings.warn(msg, FutureWarning, stacklevel=2)

        if injectables:
            msg = (
                "Passing both 'injectables' and 'services'/'service_modules' is not supported. "
                "Please use only injectables as 'services'/'service_modules' is deprecated."
            )
            raise WireupError(msg)

    if injectables:
        injectable_definitions: list[Any] = []
        injectable_modules: list[ModuleType] = []

        for injectable in injectables:
            if isinstance(injectable, ModuleType):
                injectable_modules.append(injectable)
            else:
                injectable_definitions.append(injectable)

        abstracts, impls = _merge_definitions(injectable_modules, injectable_definitions)
    else:
        abstracts, impls = _merge_definitions(service_modules, services)

    registry = ContainerRegistry(config=ConfigStore(parameters or config), abstracts=abstracts, impls=impls)
    # The container uses a dual-compiler optimization strategy:
    # 1. The singleton compiler generates optimized factories for singleton dependencies
    #    and throws errors if scoped dependencies are accessed outside a scope.
    # 2. The scoped compiler handles dependencies that require request/scope isolation.
    #
    # When entering/exiting scopes, the container switches between these compilers.
    # This eliminates the need to check lifetime rules at runtime.
    singleton_compiler = FactoryCompiler(registry, is_scoped_container=False)
    scoped_compiler = FactoryCompiler(registry, is_scoped_container=True)
    singleton_compiler.compile()
    scoped_compiler.compile()

    override_manager = OverrideManager(registry.is_type_with_qualifier_known, singleton_compiler, scoped_compiler)
    return klass(
        registry=registry,
        factory_compiler=singleton_compiler,
        scoped_compiler=scoped_compiler,
        global_scope_objects={},
        global_scope_exit_stack=[],
        override_manager=override_manager,
    )


def _merge_definitions(
    service_modules: Iterable[ModuleType] | None = None,
    services: Iterable[Any] | None = None,
) -> tuple[list[AbstractDeclaration], list[InjectableDeclaration]]:
    abstracts: list[AbstractDeclaration] = []
    impls: list[InjectableDeclaration] = []

    if services:
        for service in services:
            if not hasattr(service, "__wireup_registration__"):
                msg = f"Injectable {service} is not decorated with @abstract or @injectable."
                raise WireupError(msg)

            reg: AbstractDeclaration | InjectableDeclaration = service.__wireup_registration__

            if isinstance(reg, AbstractDeclaration):
                abstracts.append(reg)
            else:
                impls.append(reg)

    if service_modules:
        discovered_abstracts, discovered_services = discover_wireup_registrations(service_modules)
        abstracts.extend(discovered_abstracts)
        impls.extend(discovered_services)

    return abstracts, impls


def create_sync_container(
    service_modules: list[ModuleType] | None = None,
    services: list[Any] | None = None,
    parameters: dict[str, Any] | None = None,
    *,
    config: dict[str, Any] | None = None,
    injectables: list[Any] | None = None,
) -> SyncContainer:
    """Create a synchronous Wireup container.

    See the documentation for more details:
    https://maldoinc.github.io/wireup/latest/container/

    :param config: Configuration to expose to the container. Injectables or factories can
        request config via the `Inject(config="name")` annotation.
    :param injectables: A list of classes or functions decorated with `@injectable` or `@abstract` or modules containing
        injectables to register with the container instance.
    :param service_modules: Deprecated: Use injectables instead.
    :param services: Deprecated: Use injectables instead.
    :param parameters: Deprecated. Parameters was renamed to config, use that instead.
    :raises WireupError: Raised if the dependencies cannot be fully resolved.
    """
    return _create_container(
        SyncContainer,
        service_modules=service_modules,
        services=services,
        parameters=parameters,
        config=config,
        injectables=injectables,
    )


def create_async_container(
    service_modules: list[ModuleType] | None = None,
    services: list[Any] | None = None,
    parameters: dict[str, Any] | None = None,
    *,
    config: dict[str, Any] | None = None,
    injectables: list[Any] | None = None,
) -> AsyncContainer:
    """Create an asynchronous Wireup container.

    See the documentation for more details:
    https://maldoinc.github.io/wireup/latest/container/

    :param config: Configuration to expose to the container. Injectables or factories can
        request config via the `Inject(config="name")` annotation.
    :param injectables: A list of classes or functions decorated with `@injectable` or `@abstract` or modules containing
        injectables to register with the container instance.
    :param service_modules: Deprecated: Use injectables instead.
    :param services: Deprecated: Use injectables instead.
    :param parameters: Deprecated. Parameters was renamed to config, use that instead.
    :raises WireupError: Raised if the dependencies cannot be fully resolved.
    """
    return _create_container(
        AsyncContainer,
        service_modules=service_modules,
        services=services,
        parameters=parameters,
        config=config,
        injectables=injectables,
    )
