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
from wireup.ioc.types import AnnotatedParameter, AutowireTarget, ServiceLifetime
from wireup.ioc.util import is_type_autowireable, param_get_annotation

if TYPE_CHECKING:
    from collections.abc import Iterable

    from wireup.ioc.types import (
        Qualifier,
    )


class _ServiceRegistry:
    __slots__ = ("known_interfaces", "known_impls", "factory_functions", "context")

    def __init__(self) -> None:
        self.known_interfaces: dict[type, dict[Qualifier, type]] = {}
        self.known_impls: dict[type, set[Qualifier]] = defaultdict(set)
        self.factory_functions: dict[tuple[type, Qualifier], Callable[..., Any]] = {}

        self.context = InitializationContext()

    def register_service(
        self,
        klass: type,
        qualifier: Qualifier | None,
        lifetime: ServiceLifetime,
    ) -> None:
        if self.is_type_with_qualifier_known(klass, qualifier):
            raise DuplicateServiceRegistrationError(klass, qualifier)

        if klass.__base__ and self.is_interface_known(klass.__base__):
            if qualifier in self.known_interfaces[klass.__base__]:
                raise DuplicateQualifierForInterfaceError(klass, qualifier)

            self.known_interfaces[klass.__base__][qualifier] = klass

        self.known_impls[klass].add(qualifier)
        self.target_init_context(klass, lifetime)

    def register_abstract(self, klass: type) -> None:
        self.known_interfaces[klass] = defaultdict()

    def register_factory(
        self, fn: Callable[..., Any], lifetime: ServiceLifetime, qualifier: Qualifier | None = None
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
            annotated_param = param_get_annotation(parameter)

            if not annotated_param:
                continue

            # Add to the context only if it's something we can inject
            # or if it is a class that's not one of the builtins: int str dict etc.
            # This is the case for services which are only typed and do not require an annotation.
            if annotated_param.annotation or is_type_autowireable(annotated_param.klass):
                self.context.add_dependency(target, name, annotated_param)

    def get_dependency_graph(self) -> dict[type, set[type]]:
        """Return a dependency graph for the current set of registered services.

        This is based on the context's but with the following changes
        * Transient services are removed
        * Objects depending on interfaces will instead depend on all implementations of that interface.
        * Factories are replaced with the thing they produce.
        """
        factory_to_type: dict[Callable[..., Any], type[Any]] = {v: k[0] for k, v in self.factory_functions.items()}
        types_created_by_factories = set(factory_to_type.values())
        res: dict[type, set[type[Any]]] = {}

        for target, dependencies in self.context.dependencies.items():
            # If this type is being created by a factory then do not process the current entry
            # as the dependency graph for it will be processed through the factory.
            if target in types_created_by_factories:
                continue

            klass: type[Any] = factory_to_type.get(target, target)  # type: ignore[arg-type]

            if not self.is_impl_singleton(klass):
                continue

            res[klass] = {cls for cls in self._get_class_deps(dependencies.values()) if self.is_impl_singleton(cls)}

        return res

    def _get_class_deps(self, dependencies: Iterable[AnnotatedParameter]) -> set[type[Any]]:
        """Return a set with non-parameter dependencies from the given annotated parameter list."""
        current_deps: set[type[Any]] = set()

        for annotated_param in dependencies:
            if annotated_param.is_parameter or not annotated_param.klass:
                continue

            if self.is_interface_known(annotated_param.klass):
                current_deps.update(self.known_interfaces.get(annotated_param.klass, {}).values())
            else:
                current_deps.add(annotated_param.klass)
        return current_deps

    def is_impl_known(self, klass: type) -> bool:
        return klass in self.known_impls

    def is_impl_with_qualifier_known(self, klass: type, qualifier_value: Qualifier | None) -> bool:
        return klass in self.known_impls and qualifier_value in self.known_impls[klass]

    def is_type_with_qualifier_known(self, klass: type, qualifier: Qualifier | None) -> bool:
        is_known_impl = self.is_impl_with_qualifier_known(klass, qualifier)
        is_known_intf = self.__is_interface_with_qualifier_known(klass, qualifier)
        is_known_from_factory = self.is_impl_known_from_factory(klass, qualifier)

        return is_known_impl or is_known_intf or is_known_from_factory

    def __is_interface_with_qualifier_known(
        self,
        klass: type,
        qualifier: Qualifier | None,
    ) -> bool:
        return klass in self.known_interfaces and qualifier in self.known_interfaces[klass]

    def is_impl_known_from_factory(self, klass: type, qualifier: Qualifier | None) -> bool:
        return (klass, qualifier) in self.factory_functions

    def is_impl_singleton(self, klass: type) -> bool:
        return self.context.lifetime.get(klass) == ServiceLifetime.SINGLETON

    def is_interface_known(self, klass: type) -> bool:
        return klass in self.known_interfaces
