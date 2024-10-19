from __future__ import annotations

import asyncio
import functools
import inspect
import sys
import warnings
from typing import TYPE_CHECKING, Any, TypeVar, overload

from wireup.ioc.base_container import BaseContainer

if sys.version_info < (3, 9):
    from graphlib2 import TopologicalSorter
else:
    from graphlib import TopologicalSorter

from wireup.errors import (
    ContainerCloseError,
    InvalidRegistrationTypeError,
    UnknownServiceRequestedError,
    WireupError,
)
from wireup.ioc.service_registry import ServiceRegistry
from wireup.ioc.types import (
    AnyCallable,
    EmptyContainerInjectionRequest,
    Qualifier,
    ServiceLifetime,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import GeneratorType

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

    __slots__ = ("__exit_stack",)

    def __init__(self, parameter_bag: ParameterBag) -> None:
        """:param parameter_bag: ParameterBag instance holding parameter information."""
        super().__init__(registry=ServiceRegistry(), parameters=parameter_bag, overrides={})
        self.__exit_stack: list[GeneratorType[Any, Any, Any]] = []

    def get(self, klass: type[T], qualifier: Qualifier | None = None) -> T:
        """Get an instance of the requested type.

        Use this to locate services by their type but strongly prefer using injection instead.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        if res := self._overrides.get((klass, qualifier)):
            return res  # type: ignore[no-any-return]

        if self._registry.is_interface_known(klass):
            klass = self._registry.interface_resolve_impl(klass, qualifier)

        if instance := self._initialized_objects.get((klass, qualifier)):
            return instance  # type: ignore[no-any-return]

        if res := self.__create_instance(klass, qualifier):
            return res

        raise UnknownServiceRequestedError(klass)

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

    @property
    def params(self) -> ParameterBag:
        """Parameter bag associated with this container."""
        return self._params

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
        self._initialized_objects.clear()

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
        self._registry.target_init_context(fn)

        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_inner(*args: Any, **kwargs: Any) -> Any:
                return await fn(*args, **{**kwargs, **self.__callable_get_params_to_inject(fn)})

            return async_inner

        @functools.wraps(fn)
        def sync_inner(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **{**kwargs, **self.__callable_get_params_to_inject(fn)})

        return sync_inner

    def warmup(self) -> None:
        """Initialize all singleton dependencies registered in the container.

        This should be executed once all services are registered with the container. Targets of autowire will not
        be affected.
        """
        sorter = TopologicalSorter(self._registry.get_dependency_graph())

        for klass in sorter.static_order():
            for qualifier in self._registry.known_impls[klass]:
                if (klass, qualifier) not in self._initialized_objects:
                    self.get(klass, qualifier)

    def __callable_get_params_to_inject(self, fn: AnyCallable) -> dict[str, Any]:
        result: dict[str, Any] = {}
        names_to_remove: set[str] = set()

        for name, param in self._registry.context.dependencies[fn].items():
            obj, value_found = self._try_get_existing_value(param)

            if value_found or (param.klass and (obj := self.__create_instance(param.klass, param.qualifier_value))):
                result[name] = obj
            else:
                # Normally the container won't throw if it encounters a type it doesn't know about
                # But if it's explicitly marked as to be injected then we need to throw.
                if param.klass and isinstance(param.annotation, EmptyContainerInjectionRequest):
                    raise UnknownServiceRequestedError(param.klass)

                names_to_remove.add(name)

        # If autowiring, the container is assumed to be final, so unnecessary entries can be removed
        # from the context in order to speed up the autowiring process.
        if names_to_remove:
            self._registry.context.remove_dependencies(fn, names_to_remove)

        return result

    def __create_instance(self, klass: type[T], qualifier: Qualifier | None) -> T | None:
        if res := self._get_ctor(klass=klass, qualifier=qualifier):
            ctor, resolved_type = res
            instance_or_generator = ctor(**self.__callable_get_params_to_inject(ctor))

            if inspect.isgenerator(instance_or_generator):
                self.__exit_stack.append(instance_or_generator)
                instance = next(instance_or_generator)
                is_generator = True
            else:
                instance = instance_or_generator
                is_generator = False

            if self._registry.is_impl_singleton(resolved_type):
                self._initialized_objects[resolved_type, qualifier] = instance
            elif is_generator:
                msg = "Generators are not currently supported with transient-scoped dependencies."
                raise WireupError(msg)

            return instance

        return None

    def close(self) -> None:
        """Consume generator factories allowing them to properly release resources."""
        errors: list[Exception] = []

        while self.__exit_stack and (gen := self.__exit_stack.pop()):
            try:
                gen.send(None)
            except StopIteration:  # noqa: PERF203
                pass
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        if errors:
            raise ContainerCloseError(errors)
