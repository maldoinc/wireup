from __future__ import annotations

import asyncio
import functools
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

from wireup import ServiceLifetime

from .container_util import (
    AutowireTarget,
    ContainerInjectionRequest,
    ContainerProxy,
    ContainerProxyQualifier,
    ContainerProxyQualifierValue,
    ParameterWrapper,
)
from .service_registry import _ServiceRegistry
from .util import AnnotatedParameter, find_classes_in_module

if TYPE_CHECKING:
    from types import ModuleType

    from .initialization_context import InitializationContext
    from .parameter import ParameterBag

__T = TypeVar("__T")


class DependencyContainer(Generic[__T]):
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

    def __init__(self, parameter_bag: ParameterBag) -> None:
        """:param parameter_bag: ParameterBag instance holding parameter information."""
        self.__service_registry: _ServiceRegistry[__T] = _ServiceRegistry()

        self.__initialized_objects: dict[tuple[type[__T], ContainerProxyQualifierValue], __T] = {}
        self.__initialized_proxies: dict[tuple[type[__T], ContainerProxyQualifierValue], ContainerProxy[__T]] = {}

        self.params: ParameterBag = parameter_bag

    def get(self, klass: type[__T], qualifier: ContainerProxyQualifierValue = None) -> __T:
        """Get an instance of the requested type.

        Use this to locate services by their type but strongly prefer using injection instead.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        self.__assert_dependency_exists(klass, qualifier)

        # We need to lie a bit to the type checker here. Container does not inject the real object
        # but rather a proxy which will instantiate that type during first use.
        # In turn that object may get injected other proxy objects.
        # This enables lazy loading.
        return self.__get_injected_object(klass, qualifier)  # type: ignore[return-value]

    def abstract(self, klass: type[__T]) -> type[__T]:
        """Register a type as an interface.

        This type cannot be initialized directly and one of the components implementing this will be injected instead.
        """
        self.__service_registry.register_abstract(klass)

        return klass

    def register(
        self,
        obj: AutowireTarget[__T] | None = None,
        *,
        qualifier: ContainerProxyQualifierValue = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> AutowireTarget[__T] | Callable[[AutowireTarget[__T]], AutowireTarget[__T]]:
        """Register a dependency in the container.

        Use `@register` without parameters on a class or with a single parameter `@register(qualifier=name)`
        to register this with a given name when there are multiple implementations of the interface this implements.

        Use `@register` on a function to register that function as a factory method which produces an object
        that matches its return type.

        The container stores all necessary metadata for this class and the underlying class remains unmodified.
        """
        # Allow register to be used either with or without arguments
        if obj is None:

            def decorated(decorated_obj: AutowireTarget[__T]) -> AutowireTarget[__T]:
                self.__register_object(decorated_obj, qualifier, lifetime)

                return decorated_obj

            return decorated

        self.__register_object(obj, qualifier, lifetime)

        return obj

    @property
    def context(self) -> InitializationContext[__T]:
        """The initialization context for registered targets. A map between an injection target and its dependencies."""
        return self.__service_registry.context

    def __register_object(
        self,
        obj: AutowireTarget[__T],
        qualifier: ContainerProxyQualifierValue,
        lifetime: ServiceLifetime,
    ) -> None:
        if isinstance(obj, type):
            self.__service_registry.register_service(obj, qualifier, lifetime)
        else:
            self.__service_registry.register_factory(obj, lifetime)

    def autowire(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Automatically inject resources from the container to the decorated methods.

        Any arguments which the container does not know about will be ignored
        so that another decorator or framework can supply their values.
        This decorator can be used on both async and blocking methods.

        * Classes will be automatically injected.
        * Parameters need to be annotated in order for container to be able to resolve them
        * When injecting an interface for which there are multiple implementations you need to supply a qualifier
          using annotations.
        """
        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_inner(*args: Any, **kwargs: Any) -> Any:
                return await self.__autowire_inner(fn, *args, **kwargs)

            return async_inner

        @functools.wraps(fn)
        def sync_inner(*args: Any, **kwargs: Any) -> Any:
            return self.__autowire_inner(fn, *args, **kwargs)

        return sync_inner

    def register_all_in_module(self, module: ModuleType, pattern: str = "*") -> None:
        """Register all modules inside a given module.

        Useful when your components reside in one place, and you'd like to avoid having to `@register` each of them.
        Alternatively this can be used if you want to use the library without having to rely on decorators.

        See Also: `self.initialization_context` to wire parameters without having to use a default value.

        :param module: The package name to recursively search for classes.
        :param pattern: A pattern that will be fed to fnmatch to determine if a class will be registered or not.
        """
        klass: type[__T]
        for klass in find_classes_in_module(module, pattern):
            self.register(klass)

    def __autowire_inner(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        self.__service_registry.target_init_context(fn)

        return fn(*args, **{**kwargs, **self.__callable_get_params_to_inject(fn)})

    def __callable_get_params_to_inject(self, fn: Callable[..., Any]) -> dict[str, Any]:
        values_from_parameters = {}
        params = self.__service_registry.context.get(fn)

        for name, annotated_parameter in params.items():
            # Dealing with parameter, return the value as we cannot proxy int str etc.
            # We don't want to check here for none because as long as it exists in the bag, the value is good.
            if isinstance(annotated_parameter.annotation, ParameterWrapper):
                values_from_parameters[name] = self.params.get(annotated_parameter.annotation.param)
            elif obj := self.__initialize_container_proxy_object_from_parameter(annotated_parameter):
                values_from_parameters[name] = obj

        return values_from_parameters

    def __get(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> __T:
        """Create the real instances of dependencies. Additional dependencies they may have will be lazily created."""
        self.__assert_dependency_exists(klass, qualifier)
        class_to_initialize = klass

        if self.__service_registry.is_interface_known(klass) and (
            concrete_class := self.__get_concrete_class_from_interface_and_qualifier(klass, qualifier)
        ):
            class_to_initialize = concrete_class

        if self.__service_registry.is_impl_known_from_factory(class_to_initialize):
            fn = self.__service_registry.factory_functions[class_to_initialize]
            instance = fn(**self.__callable_get_params_to_inject(fn))
        else:
            args = self.__callable_get_params_to_inject(class_to_initialize)
            instance = class_to_initialize(**args)

        if self.__service_registry.is_impl_singleton(klass):
            self.__initialized_objects[class_to_initialize, qualifier] = instance

        return instance

    def __initialize_container_proxy_object_from_parameter(self, annotated_parameter: AnnotatedParameter[__T]) -> Any:
        if annotated_parameter.klass is None:
            return None

        annotated_type = annotated_parameter.klass

        if self.__service_registry.is_impl_known_from_factory(annotated_type):
            # Objects generated from factories do not have qualifiers
            return self.__get_injected_object(annotated_type, None)

        qualifier_value = (
            annotated_parameter.annotation.qualifier
            if isinstance(annotated_parameter.annotation, ContainerProxyQualifier)
            else None
        )

        if self.__service_registry.is_interface_known(annotated_parameter.klass):
            concrete_class = self.__get_concrete_class_from_interface_and_qualifier(annotated_type, qualifier_value)
            return self.__get_injected_object(concrete_class, qualifier_value)

        if self.__service_registry.is_impl_known(annotated_type):
            if not self.__service_registry.is_impl_with_qualifier_known(annotated_type, qualifier_value):
                msg = (
                    f"Cannot instantiate concrete class for {annotated_type} as qualifier '{qualifier_value}'"
                    f" is unknown. Available qualifiers: {self.__service_registry.known_impls[annotated_type]}"
                )
                raise ValueError(msg)
            return self.__get_injected_object(annotated_type, qualifier_value)

        # Normally the container won't throw if it encounters a type it doesn't know about
        # But if it's explicitly marked as to be injected then we need to throw.
        if isinstance(annotated_parameter.annotation, ContainerInjectionRequest):
            self.__assert_dependency_exists(annotated_type, qualifier=None)

        # When injecting dependencies and a qualifier is used, throw if it's being used on an unknown type.
        # This prevents the default value from being used by the runtime.
        # We don't actually want that to happen as the value is used only for hinting the container
        # and all values should be supplied.
        if qualifier_value:
            msg = f"Cannot use qualifier {qualifier_value} on a type that is not managed by the container."
            raise ValueError(msg)

        return None

    def __get_injected_object(
        self,
        klass: type[__T],
        qualifier: ContainerProxyQualifierValue,
    ) -> ContainerProxy[__T] | __T:
        """Return a container proxy or an instance of the requested singleton class if one has been initialized."""
        obj_id = klass, qualifier

        # If there's an existing instance return that directly without having to proxy it
        if instance := self.__initialized_objects.get(obj_id):
            return instance

        if self.__service_registry.is_impl_singleton(klass) and (proxy := self.__initialized_proxies.get(obj_id)):
            return proxy

        proxy = ContainerProxy(lambda: self.__get(klass, qualifier))
        self.__initialized_proxies[obj_id] = proxy

        return proxy

    def __get_concrete_class_from_interface_and_qualifier(
        self,
        klass: type[__T],
        qualifier: ContainerProxyQualifierValue,
    ) -> type[__T]:
        concrete_classes = self.__service_registry.known_interfaces.get(klass, {})

        if qualifier in concrete_classes:
            return concrete_classes[qualifier]

        # We have to raise here otherwise if we have a default hinting the qualifier for an unknown type
        # which will result in the value of the parameter being ContainerProxyQualifier.
        msg = (
            f"Cannot instantiate concrete class for {klass} as qualifier '{qualifier}' is unknown. "
            f"Available qualifiers: {set(concrete_classes.keys())}"
        )
        raise ValueError(msg)

    def __assert_dependency_exists(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> None:
        """Assert that there exists an impl with that qualifier or an interface with an impl and the same qualifier."""
        if not self.__service_registry.is_type_with_qualifier_known(klass, qualifier):
            msg = f"Cannot wire unknown class {klass}. Use @Container.{{register,abstract}} to enable autowiring"
            raise ValueError(msg)
