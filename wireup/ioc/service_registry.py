from __future__ import annotations

import inspect
import typing
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from wireup.errors import (
    DuplicateQualifierForInterfaceError,
    DuplicateServiceRegistrationError,
    FactoryDuplicateServiceRegistrationError,
    FactoryReturnTypeIsEmptyError,
    UnknownQualifiedServiceRequestedError,
)
from wireup.ioc.initialization_context import InitializationContext
from wireup.ioc.types import AnnotatedParameter, AutowireTarget, ServiceLifetime
from wireup.ioc.util import _get_globals, ensure_is_type, is_type_autowireable, param_get_annotation

if TYPE_CHECKING:
    from collections.abc import Iterable

    from wireup.ioc.types import (
        Qualifier,
    )


T = TypeVar("T")


class FactoryType(Enum):
    REGULAR = auto()
    GENERATOR = auto()
    ASYNC_GENERATOR = auto()


GENERATOR_FACTORY_TYPES = {FactoryType.GENERATOR, FactoryType.ASYNC_GENERATOR}


@dataclass
class ServiceFactory:
    factory: Callable[..., Any]
    factory_type: FactoryType


def _function_get_unwrapped_return_type(fn: Callable[..., T]) -> tuple[type[T], FactoryType] | None:
    if ret := fn.__annotations__.get("return"):
        ret = ensure_is_type(ret, globalns=_get_globals(fn))
        if not ret:
            return None

        is_gen = inspect.isgeneratorfunction(fn)
        if is_gen or inspect.isasyncgenfunction(fn):
            args = typing.get_args(ret)

            if not args:
                return None

            return args[0], FactoryType.GENERATOR if is_gen else FactoryType.ASYNC_GENERATOR

        return ret, FactoryType.REGULAR

    return None


class ServiceRegistry:
    """Container class holding service registration info and dependencies among them."""

    __slots__ = ("known_interfaces", "known_impls", "factory_functions", "context")

    def __init__(self) -> None:
        self.known_interfaces: dict[type, dict[Qualifier, type]] = {}
        self.known_impls: dict[type, set[Qualifier]] = defaultdict(set)
        self.factory_functions: dict[tuple[type, Qualifier], ServiceFactory] = {}

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
        self,
        fn: Callable[..., Any],
        lifetime: ServiceLifetime,
        qualifier: Qualifier | None = None,
    ) -> None:
        return_type_result = _function_get_unwrapped_return_type(fn)

        if return_type_result is None:
            raise FactoryReturnTypeIsEmptyError

        return_type, factory_type = return_type_result

        if self.is_impl_known_from_factory(return_type, qualifier):
            raise FactoryDuplicateServiceRegistrationError(return_type)

        if self.is_type_with_qualifier_known(return_type, qualifier):
            raise DuplicateServiceRegistrationError(return_type, qualifier=None)

        self.target_init_context(fn, lifetime=lifetime)
        self.factory_functions[return_type, qualifier] = ServiceFactory(
            factory=fn,
            factory_type=factory_type,
        )
        self.known_impls[return_type].add(qualifier)

        # The target and its lifetime just needs to be known. No need to check its dependencies
        # as the factory will be the one to create it.
        self.context.init_target(return_type, lifetime)

    def target_init_context(
        self,
        target: AutowireTarget,
        lifetime: ServiceLifetime | None = None,
    ) -> None:
        """Init and collect all the necessary dependencies to initialize the specified target."""
        if not self.context.init_target(target, lifetime):
            return

        for name, parameter in inspect.signature(target).parameters.items():
            annotated_param = param_get_annotation(parameter, globalns=_get_globals(target))

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
        # handle generators in warmup.
        factory_to_type: dict[Callable[..., Any], type[Any]] = {
            v.factory: k[0] for k, v in self.factory_functions.items()
        }
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
        """Determine if klass is known by the registry."""
        return klass in self.known_impls

    def is_impl_with_qualifier_known(self, klass: type, qualifier_value: Qualifier | None) -> bool:
        """Determine if klass represending a concrete implementation + qualifier is known by the registry."""
        return klass in self.known_impls and qualifier_value in self.known_impls[klass]

    def is_type_with_qualifier_known(self, klass: type, qualifier: Qualifier | None) -> bool:
        """Determine if klass+qualifier is known. Klass can be a concrete class or one registered as abstract."""
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

    def interface_resolve_impl(self, klass: type[T], qualifier: Qualifier | None) -> type[T]:
        """Given an interface and qualifier return the concrete implementation."""
        impls = self.known_interfaces.get(klass, {})

        if qualifier in impls:
            return impls[qualifier]

        raise UnknownQualifiedServiceRequestedError(klass, qualifier, set(impls.keys()))
