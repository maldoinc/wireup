from __future__ import annotations

import asyncio
import functools
import sys
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, TypeVar, overload

from .override_manager import OverrideManager

if sys.version_info[:2] > (3, 8):
    from graphlib import TopologicalSorter
else:
    from graphlib2 import TopologicalSorter

from wireup.errors import (
    InvalidRegistrationTypeError,
    UnknownQualifiedServiceRequestedError,
    UnknownServiceRequestedError,
    UsageOfQualifierOnUnknownObjectError,
)

from .service_registry import ServiceRegistry
from .types import (
    AnnotatedParameter,
    AnyCallable,
    EmptyContainerInjectionRequest,
    ParameterWrapper,
    Qualifier,
    ServiceLifetime,
)

if TYPE_CHECKING:
    from .initialization_context import InitializationContext
    from .parameter import ParameterBag

__T = TypeVar("__T")
__ObjectIdentifier = Tuple[type, Optional[Qualifier]]


class DependencyContainer:
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

    __slots__ = (
        "__service_registry",
        "__initialized_objects",
        "__active_overrides",
        "__override_manager",
        "__params",
    )

    def __init__(self, parameter_bag: ParameterBag) -> None:
        """:param parameter_bag: ParameterBag instance holding parameter information."""
        self.__service_registry: ServiceRegistry = ServiceRegistry()
        self.__initialized_objects: dict[__ObjectIdentifier, Any] = {}
        self.__active_overrides: dict[__ObjectIdentifier, Any] = {}
        self.__params: ParameterBag = parameter_bag
        self.__override_manager: OverrideManager = OverrideManager(
            self.__active_overrides, self.__service_registry.is_type_with_qualifier_known
        )

    def get(self, klass: type[__T], qualifier: Qualifier | None = None) -> __T:
        """Get an instance of the requested type.

        Use this to locate services by their type but strongly prefer using injection instead.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        if res := self.__active_overrides.get((klass, qualifier)):
            return res  # type: ignore[no-any-return]

        self.__assert_dependency_exists(klass, qualifier)

        if self.__service_registry.is_interface_known(klass):
            klass = self.__resolve_impl(klass, qualifier)

        return self.__get_instance(klass, qualifier)

    def abstract(self, klass: type[__T]) -> type[__T]:
        """Register a type as an interface.

        This type cannot be initialized directly and one of the components implementing this will be injected instead.
        """
        self.__service_registry.register_abstract(klass)

        return klass

    @overload
    def register(
        self,
        obj: None = None,
        *,
        qualifier: Qualifier | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> Callable[[__T], __T]:
        pass

    @overload
    def register(
        self,
        obj: __T,
        *,
        qualifier: Qualifier | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> __T:
        pass

    def register(
        self,
        obj: __T | None = None,
        *,
        qualifier: Qualifier | None = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> __T | Callable[[__T], __T]:
        """Register a dependency in the container. Dependency must be either a class or a factory function.

        * Use as a decorator without parameters @container.register on a factory function or class to register it.
        * Use as a decorator with parameters to specify qualifier and lifetime, @container.register(qualifier=...).
        * Call it directly with @container.register(some_class_or_factory, qualifier=..., lifetime=...).
        """
        # Allow register to be used either with or without arguments
        if obj is None:

            def decorated(decorated_obj: __T) -> __T:
                self.register(decorated_obj, qualifier=qualifier, lifetime=lifetime)
                return decorated_obj

            return decorated

        if isinstance(obj, type):
            self.__service_registry.register_service(obj, qualifier, lifetime)
            return obj

        if callable(obj):
            self.__service_registry.register_factory(obj, qualifier=qualifier, lifetime=lifetime)
            return obj

        raise InvalidRegistrationTypeError(obj)

    @property
    def context(self) -> InitializationContext:
        """The initialization context for registered targets. A map between an injection target and its dependencies."""
        return self.__service_registry.context

    @property
    def params(self) -> ParameterBag:
        """Parameter bag associated with this container."""
        return self.__params

    def clear_initialized_objects(self) -> None:
        """Drop references to initialized singleton objects.

        Calling this will cause the container to drop references to initialized singletons
        and cause it to create new instances when they are requested to be injected.

        This can be useful in tests in a `unittest.TestCase.setUp` method or pytest autouse=True fixture,
        allowing you to have a fresh copy of the container with no previously initialized instances
        to make test cases independent of each-other.
        """
        self.__initialized_objects.clear()

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
        self.__service_registry.target_init_context(fn)

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
        sorter = TopologicalSorter(self.__service_registry.get_dependency_graph())

        for klass in sorter.static_order():
            for qualifier in self.__service_registry.known_impls[klass]:
                if (klass, qualifier) not in self.__initialized_objects:
                    self.__create_instance(klass, qualifier)

    @property
    def override(self) -> OverrideManager:
        """Override registered container services with new values."""
        return self.__override_manager

    def __callable_get_params_to_inject(self, fn: AnyCallable) -> dict[str, Any]:
        values_from_parameters: dict[str, Any] = {}
        params = self.__service_registry.context.dependencies[fn]
        names_to_remove: set[str] = set()

        for name, param in params.items():
            # This block is particularly crucial for performance and has to be written to be as fast as possible.

            # Check if there's already an instantiated object with this id which can be directly injected
            obj_id = param.klass, param.qualifier_value

            if param.klass and (obj := self.__active_overrides.get(obj_id, self.__initialized_objects.get(obj_id))):  # type: ignore[arg-type]
                values_from_parameters[name] = obj
            # Dealing with parameter
            # Don't check here for none because as long as it exists in the bag, the value is good.
            elif isinstance(param.annotation, ParameterWrapper):
                values_from_parameters[name] = self.params.get(param.annotation.param)
            elif param.klass and (obj := self.__get_instance_from_parameter(param)):
                values_from_parameters[name] = obj
            else:
                names_to_remove.add(name)

        # If autowiring, the container is assumed to be final, so unnecessary entries can be removed
        # from the context in order to speed up the autowiring process.
        if names_to_remove:
            self.context.remove_dependencies(fn, names_to_remove)

        return values_from_parameters

    def __create_instance(self, klass: type[__T], qualifier: Qualifier | None) -> __T:
        """Create the real instances of dependencies. Additional dependencies they may have will be lazily created."""
        self.__assert_dependency_exists(klass, qualifier)
        obj_id = klass, qualifier

        if self.__service_registry.is_interface_known(klass):
            klass = self.__resolve_impl(klass, qualifier)

        if fn := self.__service_registry.factory_functions.get(obj_id):
            instance = fn(**self.__callable_get_params_to_inject(fn))
        else:
            args = self.__callable_get_params_to_inject(klass)
            instance = klass(**args)

        if self.__service_registry.is_impl_singleton(klass):
            self.__initialized_objects[obj_id] = instance

        return instance  # type: ignore[no-any-return]

    def __get_instance_from_parameter(self, annotated_parameter: AnnotatedParameter) -> Any:
        # Disable type checker here as the only caller ensures that klass is not none to avoid the call entirely.
        annotated_type: type = annotated_parameter.klass  # type: ignore[assignment]
        qualifier_value = annotated_parameter.qualifier_value

        if self.__service_registry.is_impl_known_from_factory(annotated_type, qualifier_value):
            # Objects generated from factories do not have qualifiers
            return self.__get_instance(annotated_type, None)

        if self.__service_registry.is_interface_known(annotated_type):
            concrete_class = self.__resolve_impl(annotated_type, qualifier_value)
            return self.__get_instance(concrete_class, qualifier_value)

        if self.__service_registry.is_impl_known(annotated_type):
            if not self.__service_registry.is_impl_with_qualifier_known(annotated_type, qualifier_value):
                raise UnknownQualifiedServiceRequestedError(
                    annotated_type,
                    qualifier_value,
                    self.__service_registry.known_impls[annotated_type],
                )
            return self.__get_instance(annotated_type, qualifier_value)

        # Normally the container won't throw if it encounters a type it doesn't know about
        # But if it's explicitly marked as to be injected then we need to throw.
        if isinstance(annotated_parameter.annotation, EmptyContainerInjectionRequest):
            raise UnknownServiceRequestedError(annotated_type)

        # When injecting dependencies and a qualifier is used, throw if it's being used on an unknown type.
        # This prevents the default value from being used by the runtime.
        # We don't actually want that to happen as the value is used only for hinting the container
        # and all values should be supplied.
        if qualifier_value:
            raise UsageOfQualifierOnUnknownObjectError(qualifier_value)

        return None

    def __get_instance(self, klass: type[__T], qualifier: Qualifier | None) -> __T:
        """Return an instance of the requested singleton class if one has been initialized."""
        obj_id = klass, qualifier

        if instance := self.__initialized_objects.get(obj_id):
            return instance  # type: ignore[no-any-return]

        if not self.__service_registry.is_impl_singleton(klass):
            return self.__create_instance(klass, qualifier)

        return self.__create_instance(klass, qualifier)

    def __resolve_impl(self, klass: type, qualifier: Qualifier | None) -> type:
        impls = self.__service_registry.known_interfaces.get(klass, {})

        if qualifier in impls:
            return impls[qualifier]

        raise UnknownQualifiedServiceRequestedError(klass, qualifier, set(impls.keys()))

    def is_type_known(self, klass: type) -> bool:
        """Given a class type return True if's registered in the container as a service or interface."""
        return self.__service_registry.is_impl_known(klass) or self.__service_registry.is_interface_known(klass)

    def __assert_dependency_exists(self, klass: type, qualifier: Qualifier | None) -> None:
        """Assert that there exists an impl with that qualifier or an interface with an impl and the same qualifier."""
        if not self.__service_registry.is_type_with_qualifier_known(klass, qualifier):
            raise UnknownServiceRequestedError(klass)
