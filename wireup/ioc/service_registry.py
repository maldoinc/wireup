from __future__ import annotations

import inspect
from collections import defaultdict
from inspect import Parameter
from typing import TYPE_CHECKING, Any, Callable

from wireup.errors import (
    DuplicateQualifierForInterfaceError,
    DuplicateServiceRegistrationError,
    FactoryDuplicateServiceRegistrationError,
    FactoryReturnTypeIsEmptyError,
)
from wireup.ioc.initialization_context import InitializationContext
from wireup.ioc.types import AutowireTarget, InjectableType, ServiceLifetime
from wireup.ioc.util import is_type_autowireable, parameter_get_type_and_annotation

if TYPE_CHECKING:
    from wireup.ioc.types import (
        ContainerProxyQualifierValue,
    )


class _ServiceRegistry:
    __slots__ = ("known_interfaces", "known_impls", "factory_functions", "context")

    def __init__(self) -> None:
        self.known_interfaces: dict[type, dict[ContainerProxyQualifierValue, type]] = {}
        self.known_impls: dict[type, set[ContainerProxyQualifierValue]] = defaultdict(set)
        self.factory_functions: dict[tuple[type, ContainerProxyQualifierValue], Callable[..., Any]] = {}

        self.context = InitializationContext()

    def register_service(
        self,
        klass: type,
        qualifier: ContainerProxyQualifierValue,
        lifetime: ServiceLifetime,
    ) -> None:
        if self.is_type_with_qualifier_known(klass, qualifier):
            raise DuplicateServiceRegistrationError(klass, qualifier)

        if self.is_interface_known(klass.__base__):
            if qualifier in self.known_interfaces[klass.__base__]:
                raise DuplicateQualifierForInterfaceError(klass, qualifier)

            self.known_interfaces[klass.__base__][qualifier] = klass

        self.known_impls[klass].add(qualifier)
        self.target_init_context(klass, lifetime)

    def register_abstract(self, klass: type) -> None:
        self.known_interfaces[klass] = defaultdict()

    def register_factory(
        self, fn: Callable[..., Any], lifetime: ServiceLifetime, qualifier: ContainerProxyQualifierValue = None
    ) -> None:
        return_type = inspect.signature(fn).return_annotation

        if return_type is Parameter.empty:
            raise FactoryReturnTypeIsEmptyError

        if self.is_impl_known_from_factory(return_type, qualifier):
            raise FactoryDuplicateServiceRegistrationError(return_type)

        if self.is_type_with_qualifier_known(return_type, qualifier):
            raise DuplicateServiceRegistrationError(return_type, qualifier=None)

        self.target_init_context(fn, lifetime=lifetime)
        self.factory_functions[return_type, qualifier] = fn
        self.known_impls[return_type].add(qualifier)

        # The target and its lifetime just needs to be known. No need to check its dependencies
        # as the factory will be the one to create it.
        self.context.init_target(return_type, lifetime)

    def target_init_context(self, target: AutowireTarget, lifetime: ServiceLifetime | None = None) -> None:
        """Init and collect all the necessary dependencies to initialize the specified target."""
        if not self.context.init_target(target, lifetime):
            return

        for name, parameter in inspect.signature(target).parameters.items():
            annotated_param = parameter_get_type_and_annotation(parameter)

            if not (annotated_param.klass or annotated_param.annotation):
                continue

            # Add to the context only if it's something we can inject
            # or if it is a class that's not one of the builtins: int str dict etc.
            # This is the case for services which are only typed and do not require an annotation.
            if isinstance(annotated_param.annotation, InjectableType) or is_type_autowireable(annotated_param.klass):
                self.context.add_dependency(target, name, annotated_param)

    def get_dependency_graph(self) -> dict[type, set[type]]:
        """Return a dependency graph for the current set of registered services.

        This is based on the context's but with the following changes
        * Transient services are removed
        * Objects depending on interfaces will instead depend on all implementations of that interface.
        * Factories are replaced with the thing they produce.
        """
        factory_to_type = {v: k[0] for k, v in self.factory_functions.items()}
        res: dict[type, set[type]] = {}
        for target, dependencies in self.context.dependencies.items():
            if not isinstance(target, type):
                continue

            klass = factory_to_type.get(target, target)

            if not self.is_impl_singleton(klass):
                continue

            res[klass] = set()
            current_deps: list[type] = []

            for annotated_param in dependencies.values():
                if annotated_param.is_parameter or not annotated_param.klass:
                    continue

                dependency = annotated_param.klass

                if self.is_interface_known(dependency):
                    current_deps.extend(self.known_interfaces.get(dependency, {}).values())
                else:
                    current_deps.append(dependency)

            for dep in current_deps:
                if self.is_impl_singleton(dep):
                    res[klass].add(dep)

        return res

    def is_impl_known(self, klass: type) -> bool:
        return klass in self.known_impls

    def is_impl_with_qualifier_known(self, klass: type, qualifier_value: ContainerProxyQualifierValue) -> bool:
        return klass in self.known_impls and qualifier_value in self.known_impls[klass]

    def is_type_with_qualifier_known(self, klass: type, qualifier: ContainerProxyQualifierValue) -> bool:
        is_known_impl = self.is_impl_with_qualifier_known(klass, qualifier)
        is_known_intf = self.__is_interface_with_qualifier_known(klass, qualifier)
        is_known_from_factory = self.is_impl_known_from_factory(klass, qualifier)

        return is_known_impl or is_known_intf or is_known_from_factory

    def __is_interface_with_qualifier_known(
        self,
        klass: type,
        qualifier: ContainerProxyQualifierValue,
    ) -> bool:
        return klass in self.known_interfaces and qualifier in self.known_interfaces[klass]

    def is_impl_known_from_factory(self, klass: type, qualifier: ContainerProxyQualifierValue) -> bool:
        return (klass, qualifier) in self.factory_functions

    def is_impl_singleton(self, klass: type) -> bool:
        return self.context.lifetime.get(klass) == ServiceLifetime.SINGLETON

    def is_interface_known(self, klass: type) -> bool:
        return klass in self.known_interfaces
