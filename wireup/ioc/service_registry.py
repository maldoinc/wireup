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
    FactoryReturnTypeIsEmptyError,
    UnknownQualifiedServiceRequestedError,
)
from wireup.ioc.initialization_context import InitializationContext, InjectionTarget
from wireup.ioc.types import ServiceLifetime
from wireup.ioc.util import _get_globals, ensure_is_type, is_type_injectable, param_get_annotation

if TYPE_CHECKING:
    from wireup.ioc.types import (
        Qualifier,
    )


T = TypeVar("T")


class FactoryType(Enum):
    REGULAR = auto()
    COROUTINE_FN = auto()
    GENERATOR = auto()
    ASYNC_GENERATOR = auto()


GENERATOR_FACTORY_TYPES = {FactoryType.GENERATOR, FactoryType.ASYNC_GENERATOR}


@dataclass
class ServiceFactory:
    factory: Callable[..., Any]
    factory_type: FactoryType


def _function_get_unwrapped_return_type(fn: Callable[..., T]) -> tuple[type[T], FactoryType] | None:
    if isinstance(fn, type):
        return fn, FactoryType.REGULAR

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

        return ret, FactoryType.COROUTINE_FN if inspect.iscoroutinefunction(fn) else FactoryType.REGULAR

    return None


class ServiceRegistry:
    """Container class holding service registration info and dependencies among them."""

    __slots__ = ("context", "factories", "impls", "interfaces")

    def __init__(self) -> None:
        self.interfaces: dict[type, dict[Qualifier, type]] = {}
        self.impls: dict[type, set[Qualifier]] = defaultdict(set)
        self.factories: dict[tuple[type, Qualifier], ServiceFactory] = {}

        self.context = InitializationContext()

    def register(
        self,
        obj: Callable[..., Any],
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
        qualifier: Qualifier | None = None,
    ) -> None:
        return_type_result = _function_get_unwrapped_return_type(obj)

        if return_type_result is None:
            raise FactoryReturnTypeIsEmptyError

        klass, factory_type = return_type_result

        if self.is_type_with_qualifier_known(klass, qualifier):
            raise DuplicateServiceRegistrationError(klass, qualifier=qualifier)

        def discover_interfaces(bases: tuple[type, ...]) -> None:
            for base in bases:
                if base and self.is_interface_known(base):
                    if qualifier in self.interfaces[base]:
                        raise DuplicateQualifierForInterfaceError(klass, qualifier)

                    self.interfaces[base][qualifier] = klass
                discover_interfaces(base.__bases__)

        if hasattr(klass, "__bases__"):
            discover_interfaces(klass.__bases__)

        self.target_init_context(obj, lifetime=lifetime)
        self.factories[klass, qualifier] = ServiceFactory(
            factory=obj,
            factory_type=factory_type,
        )
        self.impls[klass].add(qualifier)
        self.context.init_target(klass, lifetime)

    def register_abstract(self, klass: type) -> None:
        self.interfaces[klass] = {}

    def target_init_context(
        self,
        target: InjectionTarget,
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
            if annotated_param.annotation or is_type_injectable(annotated_param.klass):
                self.context.add_dependency(target, name, annotated_param)

    def is_impl_with_qualifier_known(self, klass: type, qualifier_value: Qualifier | None) -> bool:
        """Determine if klass represending a concrete implementation + qualifier is known by the registry."""
        return klass in self.impls and qualifier_value in self.impls[klass]

    def is_type_with_qualifier_known(self, klass: type, qualifier: Qualifier | None) -> bool:
        """Determine if klass+qualifier is known. Klass can be a concrete class or one registered as abstract."""
        is_known_impl = self.is_impl_with_qualifier_known(klass, qualifier)
        is_known_intf = self.__is_interface_with_qualifier_known(klass, qualifier)

        return is_known_impl or is_known_intf

    def __is_interface_with_qualifier_known(
        self,
        klass: type,
        qualifier: Qualifier | None,
    ) -> bool:
        return klass in self.interfaces and qualifier in self.interfaces[klass]

    def is_interface_known(self, klass: type) -> bool:
        return klass in self.interfaces

    def interface_resolve_impl(self, klass: type[T], qualifier: Qualifier | None) -> type[T]:
        """Given an interface and qualifier return the concrete implementation."""
        impls = self.interfaces.get(klass, {})

        if qualifier in impls:
            return impls[qualifier]

        raise UnknownQualifiedServiceRequestedError(klass, qualifier, set(impls.keys()))
