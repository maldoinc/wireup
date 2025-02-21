from __future__ import annotations

import sys
import warnings
from typing import TYPE_CHECKING, Any, TypeVar, overload

from wireup.decorators import make_inject_decorator
from wireup.ioc._exit_stack import async_clean_exit_stack, clean_exit_stack
from wireup.ioc.base_container import BaseContainer
from wireup.ioc.service_registry import ServiceRegistry

if sys.version_info < (3, 9):
    from graphlib2 import TopologicalSorter
else:
    from graphlib import TopologicalSorter

from wireup.errors import (
    InvalidRegistrationTypeError,
)
from wireup.ioc.types import (
    AnyCallable,
    ContainerObjectIdentifier,
    ContainerScope,
    Qualifier,
    ServiceLifetime,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from wireup.ioc.initialization_context import InitializationContext
    from wireup.ioc.parameter import ParameterBag

T = TypeVar("T")


class DependencyContainer(BaseContainer):
    """Dependency Injection and Service Locator container registry.

    This contains all the necessary information to initialize registered classes.
    Objects instantiated by the container are lazily loaded and initialized only on first use.

    Provides the following decorators: `register`, `abstract` and `autowire`. Use register on factory functions
    and concrete classes which are to be injected from the container.
    Abstract classes are to be used as interfaces and will not be injected directly, rather concrete classes
    which implement them will be injected instead.

    Use the `autowire` decorator on methods where dependency injection must be performed.
    Services will be injected automatically where possible. Parameters will have to be annotated as they cannot
    be located from type alone.
    """

    __slots__ = ("_autowire",)

    def __init__(
        self,
        parameter_bag: ParameterBag,
        registry: ServiceRegistry | None = None,
        overrides: dict[ContainerObjectIdentifier, Any] | None = None,
        global_scope: ContainerScope | None = None,
        current_scope: ContainerScope | None = None,
    ) -> None:
        """:param parameter_bag: ParameterBag instance holding parameter information."""
        super().__init__(
            registry=registry or ServiceRegistry(),
            parameters=parameter_bag,
            overrides={} if overrides is None else overrides,
            global_scope=global_scope or ContainerScope(),
            current_scope=current_scope,
        )
        self._autowire = make_inject_decorator(self)

    get = BaseContainer._get
    aget = BaseContainer._async_get

    def abstract(self, klass: type[T]) -> type[T]:
        """Register a type as an interface.

        This type cannot be initialized directly and one of the components implementing this will be injected instead.
        """
        self._registry.register_abstract(klass)

        return klass

    @overload
    def register(
        self,
        obj: None = None,
        *,
        qualifier: Qualifier | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> Callable[[T], T]:
        pass

    @overload
    def register(
        self,
        obj: T,
        *,
        qualifier: Qualifier | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> T:
        pass

    def register(
        self,
        obj: T | None = None,
        *,
        qualifier: Qualifier | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> T | Callable[[T], T]:
        """Register a dependency in the container. Dependency must be either a class or a factory function.

        * Use as a decorator without parameters @container.register on a factory function or class to register it.
        * Use as a decorator with parameters to specify qualifier and lifetime, @container.register(qualifier=...).
        * Call it directly with @container.register(some_class_or_factory, qualifier=..., lifetime=...).
        """
        # Allow register to be used either with or without arguments
        if obj is None:

            def decorated(decorated_obj: T) -> T:
                self.register(decorated_obj, qualifier=qualifier, lifetime=lifetime)
                return decorated_obj

            return decorated

        if isinstance(obj, type):
            self._registry.register_service(obj, qualifier, lifetime)
            return obj

        if callable(obj):
            self._registry.register_factory(obj, qualifier=qualifier, lifetime=lifetime)
            return obj

        raise InvalidRegistrationTypeError(obj)

    @property
    def context(self) -> InitializationContext:
        """The initialization context for registered targets. A map between an injection target and its dependencies."""
        warnings.warn(
            "Using the initialization context directly is deprecated. "
            "Register your services using @service/@abstract. "
            "See: https://maldoinc.github.io/wireup/latest/getting_started/",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._registry.context

    def clear_initialized_objects(self) -> None:
        """Drop references to initialized singleton objects.

        Calling this will cause the container to drop references to initialized singletons
        and cause it to create new instances when they are requested to be injected.

        This can be useful in tests in a `unittest.TestCase.setUp` method or pytest autouse=True fixture,
        allowing you to have a fresh copy of the container with no previously initialized instances
        to make test cases independent of each-other.
        """
        warnings.warn(
            "Using clear_initialized_objects is deprecated. "
            "Recreate the container if you want to reset its state. "
            "See: https://maldoinc.github.io/wireup/latest/testing/",
            DeprecationWarning,
            stacklevel=2,
        )
        self._global_scope.objects.clear()

    def autowire(self, fn: AnyCallable) -> AnyCallable:
        """Automatically inject resources from the container to the decorated methods.

        Any arguments which the container does not know about will be ignored
        so that another decorator or framework can supply their values.
        This decorator can be used on both async and blocking methods.

        * Classes will be automatically injected.
        * Parameters need to be annotated in order for container to be able to resolve them
        * When injecting an interface for which there are multiple implementations you need to supply a qualifier
          using annotations.
        """
        return self._autowire(fn)  # type: ignore[no-any-return]

    def warmup(self) -> None:
        """Initialize all singleton dependencies registered in the container.

        This should be executed once all services are registered with the container. Targets of autowire will not
        be affected.
        """
        sorter = TopologicalSorter(self._registry.get_dependency_graph())

        for klass in sorter.static_order():
            for qualifier in self._registry.known_impls[klass]:
                if (klass, qualifier) not in self._global_scope.objects:
                    self.get(klass, qualifier)

    def close(self) -> None:
        """Consume generator factories allowing them to properly release resources."""
        clean_exit_stack(self._global_scope.exit_stack)

    async def aclose(self) -> None:
        """Consume generator factories allowing them to properly release resources."""
        await async_clean_exit_stack(self._global_scope.exit_stack)
