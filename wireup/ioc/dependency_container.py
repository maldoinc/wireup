from __future__ import annotations

import asyncio
import functools
from typing import TYPE_CHECKING, Any, Callable

from graphlib2 import TopologicalSorter

from wireup.errors import (
    UnknownQualifiedServiceRequestedError,
    UnknownServiceRequestedError,
    UsageOfQualifierOnUnknownObjectError,
)

from .proxy import ContainerProxy
from .service_registry import _ServiceRegistry
from .types import (
    AnnotatedParameter,
    AnyCallable,
    AutowireTarget,
    ContainerProxyQualifierValue,
    EmptyContainerInjectionRequest,
    ParameterWrapper,
    ServiceLifetime,
)

if TYPE_CHECKING:
    from .initialization_context import InitializationContext
    from .parameter import ParameterBag


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
        "__initialized_proxies",
        "__params",
    )

    def __init__(self, parameter_bag: ParameterBag) -> None:
        """:param parameter_bag: ParameterBag instance holding parameter information."""
        self.__service_registry: _ServiceRegistry = _ServiceRegistry()
        self.__initialized_objects: dict[tuple[type, ContainerProxyQualifierValue], Any] = {}
        self.__initialized_proxies: dict[tuple[type, ContainerProxyQualifierValue], ContainerProxy[Any]] = {}
        self.__params: ParameterBag = parameter_bag

    def get(self, klass: type, qualifier: ContainerProxyQualifierValue = None) -> Any:
        """Get an instance of the requested type.

        Use this to locate services by their type but strongly prefer using injection instead.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        self.__assert_dependency_exists(klass, qualifier)

        return self.__get_injected_object(klass, qualifier)

    def abstract(self, klass: type) -> type:
        """Register a type as an interface.

        This type cannot be initialized directly and one of the components implementing this will be injected instead.
        """
        self.__service_registry.register_abstract(klass)

        return klass

    def register(
        self,
        obj: AutowireTarget | None = None,
        *,
        qualifier: ContainerProxyQualifierValue = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> AutowireTarget | Callable[[AutowireTarget], AutowireTarget]:
        """Register a dependency in the container.

        Use `@register` without parameters on a class or with a single parameter `@register(qualifier=name)`
        to register this with a given name when there are multiple implementations of the interface this implements.

        Use `@register` on a function to register that function as a factory method which produces an object
        that matches its return type.

        The container stores all necessary metadata for this class and the underlying class remains unmodified.
        """
        # Allow register to be used either with or without arguments
        if obj is None:

            def decorated(decorated_obj: AutowireTarget) -> AutowireTarget:
                self.__register_object(decorated_obj, qualifier, lifetime)

                return decorated_obj

            return decorated

        self.__register_object(obj, qualifier, lifetime)

        return obj

    @property
    def context(self) -> InitializationContext:
        """The initialization context for registered targets. A map between an injection target and its dependencies."""
        return self.__service_registry.context

    @property
    def params(self) -> ParameterBag:
        """Parameter bag associated with this container."""
        return self.__params

    def __register_object(
        self,
        obj: AutowireTarget,
        qualifier: ContainerProxyQualifierValue,
        lifetime: ServiceLifetime,
    ) -> None:
        if isinstance(obj, type):
            self.__service_registry.register_service(obj, qualifier, lifetime)
        else:
            self.__service_registry.register_factory(obj, lifetime)

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
                return await fn(*args, **kwargs, **self.__callable_get_params_to_inject(fn))

            return async_inner

        @functools.wraps(fn)
        def sync_inner(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs, **self.__callable_get_params_to_inject(fn))

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
                    instance = klass(**self.__callable_get_params_to_inject(klass))
                    self.__initialized_objects[klass, qualifier] = instance

    def __callable_get_params_to_inject(self, fn: AnyCallable) -> dict[str, Any]:
        values_from_parameters = {}
        params = self.__service_registry.context.dependencies[fn]
        names_to_remove: set[str] = set()

        for name, annotated_parameter in params.items():
            # Check if there's already an instantiated object with this id which can be directly injected
            obj_id = annotated_parameter.klass, annotated_parameter.qualifier_value

            if obj := self.__initialized_objects.get(obj_id):  # type: ignore[arg-type]
                values_from_parameters[name] = obj
            # Dealing with parameter, return the value as we cannot proxy int str etc.
            # We don't want to check here for none because as long as it exists in the bag, the value is good.
            elif isinstance(annotated_parameter.annotation, ParameterWrapper):
                values_from_parameters[name] = self.params.get(annotated_parameter.annotation.param)
            elif annotated_parameter.klass and (
                obj := self.__initialize_container_proxy_object_from_parameter(annotated_parameter)
            ):
                values_from_parameters[name] = obj
            else:
                names_to_remove.add(name)

        # If autowiring, the container is assumed to be final, so unnecessary entries can be removed
        # from the context in order to speed up the autowiring process.
        if names_to_remove:
            self.context.remove_dependencies(fn, names_to_remove)

        return values_from_parameters

    def __get(self, klass: type, qualifier: ContainerProxyQualifierValue) -> Any:
        """Create the real instances of dependencies. Additional dependencies they may have will be lazily created."""
        self.__assert_dependency_exists(klass, qualifier)

        if self.__service_registry.is_interface_known(klass) and (
            concrete_class := self.__get_concrete_class_from_interface_and_qualifier(klass, qualifier)
        ):
            class_to_initialize = concrete_class
        else:
            class_to_initialize = klass

        if self.__service_registry.is_impl_known_from_factory(class_to_initialize):
            fn = self.__service_registry.factory_functions[class_to_initialize]
            instance = fn(**self.__callable_get_params_to_inject(fn))
        else:
            args = self.__callable_get_params_to_inject(class_to_initialize)
            instance = class_to_initialize(**args)

        if self.__service_registry.is_impl_singleton(klass):
            self.__initialized_objects[class_to_initialize, qualifier] = instance

        return instance

    def __initialize_container_proxy_object_from_parameter(self, annotated_parameter: AnnotatedParameter) -> Any:
        # Disable type checker here as the only caller ensures that klass is not none to avoid the call entirely.
        annotated_type: type = annotated_parameter.klass  # type: ignore[assignment]

        if self.__service_registry.is_impl_known_from_factory(annotated_type):
            # Objects generated from factories do not have qualifiers
            return self.__get_injected_object(annotated_type, None)

        qualifier_value = annotated_parameter.qualifier_value

        if self.__service_registry.is_interface_known(annotated_type):
            concrete_class = self.__get_concrete_class_from_interface_and_qualifier(annotated_type, qualifier_value)
            return self.__get_injected_object(concrete_class, qualifier_value)

        if self.__service_registry.is_impl_known(annotated_type):
            if not self.__service_registry.is_impl_with_qualifier_known(annotated_type, qualifier_value):
                raise UnknownQualifiedServiceRequestedError(
                    annotated_type,
                    qualifier_value,
                    self.__service_registry.known_impls[annotated_type],
                )
            return self.__get_injected_object(annotated_type, qualifier_value)

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

    def __get_injected_object(
        self,
        klass: type,
        qualifier: ContainerProxyQualifierValue,
    ) -> ContainerProxy[Any] | Any:
        """Return a container proxy or an instance of the requested singleton class if one has been initialized."""
        obj_id = klass, qualifier

        # If there's an existing instance return that directly without having to proxy it
        if instance := self.__initialized_objects.get(obj_id):
            return instance

        if not self.__service_registry.is_impl_singleton(klass):
            return ContainerProxy(lambda: self.__get(klass, qualifier))

        if proxy := self.__initialized_proxies.get(obj_id):
            return proxy

        proxy = ContainerProxy(lambda: self.__get(klass, qualifier))
        self.__initialized_proxies[obj_id] = proxy

        return proxy

    def __get_concrete_class_from_interface_and_qualifier(
        self,
        klass: type,
        qualifier: ContainerProxyQualifierValue,
    ) -> type:
        concrete_classes = self.__service_registry.known_interfaces.get(klass, {})

        if qualifier in concrete_classes:
            return concrete_classes[qualifier]

        # We have to raise here otherwise if we have a default hinting the qualifier for an unknown type
        # which will result in the value of the parameter being ContainerProxyQualifier.
        raise UnknownQualifiedServiceRequestedError(klass, qualifier, set(concrete_classes.keys()))

    def __assert_dependency_exists(self, klass: type, qualifier: ContainerProxyQualifierValue) -> None:
        """Assert that there exists an impl with that qualifier or an interface with an impl and the same qualifier."""
        if not self.__service_registry.is_type_with_qualifier_known(klass, qualifier):
            raise UnknownServiceRequestedError(klass)
