from __future__ import annotations

import asyncio
import functools
import inspect
from collections import defaultdict
from inspect import Parameter
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from .container_util import (
    ContainerProxy,
    ContainerProxyQualifier,
    ContainerProxyQualifierValue,
    DependencyInitializationContext,
    ParameterWrapper,
    _ContainerObjectIdentifier,
)
from .util import find_classes_in_module

if TYPE_CHECKING:
    from types import ModuleType

    from .parameter import ParameterBag

__T = TypeVar("__T")


class DependencyContainer:
    """Dependency Injection and Service Locator container registry.

    This contains all the necessary information to initialize registered classes.
    Objects instantiated by the container are lazily loaded and initialized only on first use.

    Provides the following decorators: `register`, `abstract` and `autowire`. Use register on factory functions
    and concrete classes which are to be injected from the container.
    Abstract classes are to be used as interfaces and will not be injected directly, rather concrete classes
    which implement them will be injected instead.

    Use autowire decorator on methods where dependency injection must be performed.
    To enable parameter injection use default values for parameters in conjunction with the wire method.

    !!! note
        Fastapi users MUST use ` = .wire()` method without arguments when injecting dependencies.
    """

    def __init__(self, parameter_bag: ParameterBag) -> None:
        """:param parameter_bag: ParameterBag instance holding parameter information."""
        self.__known_interfaces: dict[type[__T], dict[str, type[__T]]] = {}
        self.__known_impls: dict[type[__T], set[str]] = defaultdict(set)
        self.__initialized_objects: dict[_ContainerObjectIdentifier, object] = {}
        self.__factory_functions: dict[type[__T], Callable[..., __T]] = {}
        self.params: ParameterBag = parameter_bag
        self.initialization_context = DependencyInitializationContext()

    def get(self, klass: type[__T], qualifier: ContainerProxyQualifierValue = None) -> __T:
        """Get an instance of the requested type. Returns an existing initialized instance when possible.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return:
        """
        self.__assert_dependency_exists(klass, qualifier)

        return self.__get_proxy_object(klass, qualifier)

    def abstract(self, klass: type[__T]) -> type[__T]:
        """Register a type as an interface.

        This type cannot be initialized directly and one of the components implementing this will be injected instead.
        """
        self.__known_interfaces[klass] = defaultdict()

        return klass

    def register(
        self,
        obj: type[__T] | Callable | None = None,
        *,
        qualifier: ContainerProxyQualifierValue = None,
    ) -> type[__T]:
        """Register a dependency in the container.

        Use `@register` without parameters on a class
        or with a single parameter `@register(qualifier=name)` to register this with a given name
        when there are multiple implementations of the interface this implements.

        Use @register on a function to register that function as a factory method which produces an object
        that matches its return type. Use this for objects that the container does not own but should be able to build.

        The container stores all necessary metadata for this class and the underlying class remains unmodified.
        """
        # Allow register to be used either with or without arguments
        if obj is None:

            def decorated(inner_class: type[__T]) -> type[__T]:
                return self.__register_inner(inner_class, qualifier)

            return decorated

        if inspect.isclass(obj):
            return self.__register_inner(obj, qualifier)

        self.__register_factory_inner(obj)

        return obj

    def autowire(self, fn: Callable) -> Callable:
        """Automatically inject resources from the container to the decorated methods.

        Any arguments which the container does not know about will be ignored
        so that another decorator or framework can supply their values.
        This decorator can be used on both async and blocking methods.

        * Classes will be automatically injected.
        * Parameters need a value to be provided via `.wire(param=)` or `.wire(expr=)` using a default value.
        * When injecting an interface for which there are multiple implementations you need to supply a qualifier
          via `.wire(qualifier=)` using a default value.

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

    def __register_factory_inner(self, fn: Callable[[], __T]) -> None:
        return_type = inspect.signature(fn).return_annotation

        if return_type is Parameter.empty:
            msg = "Factory functions must specify a return type denoting the type of dependency it can create."
            raise ValueError(msg)

        if self.__is_impl_known_from_factory(return_type):
            msg = f"A function is already registered as a factory for dependency type {return_type}."
            raise ValueError(msg)

        if self.__is_impl_known(return_type):
            msg = f"Cannot register factory function as type {return_type} is already known by the container."
            raise ValueError(msg)

        self.__factory_functions[return_type] = fn

    def register_all_in_module(self, module: ModuleType, pattern: str = "*") -> None:
        """Register all modules inside a given module.

        Useful when your components reside in one place, and you'd like to avoid having to `@register` each of them.
        Alternatively this can be used if you wish to use the library without having to rely on decorators.

        See Also: `self.initialization_context` to wire parameters without having to use a default value.

        :param module: The package name to recursively search for classes.
        :param pattern: A pattern that will be fed to fnmatch to determine if a class will be registered or not.
        """
        for klass in find_classes_in_module(module, pattern):
            self.register(klass)

    def __register_inner(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> type[__T]:
        if self.__is_dependency_known(klass, qualifier):
            msg = f"Cannot register type {klass} with qualifier '{qualifier}' as it already exists."
            raise ValueError(msg)

        if klass.__base__ in self.__known_interfaces:
            if qualifier in self.__known_interfaces[klass.__base__]:
                msg = (
                    f"Cannot register implementation class {klass} for {klass.__base__} "
                    f"with qualifier '{qualifier}' as it already exists"
                )
                raise ValueError(msg)

            self.__known_interfaces[klass.__base__][qualifier] = klass

        self.__known_impls[klass].add(qualifier)

        return klass

    def __autowire_inner(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return fn(*args, **{**kwargs, **self.__callable_get_params_to_inject(fn)})

    def __callable_get_params_to_inject(self, fn: Callable[..., Any], klass: type[__T] | None = None) -> dict:
        params_from_context = {
            name: self.params.get(wrapper.param) for name, wrapper in self.initialization_context.context[klass].items()
        }

        values_from_parameters = {}
        for name, parameter in inspect.signature(fn).parameters.items():
            if obj := self.__get_container_dependency_or_param(parameter):
                values_from_parameters[name] = obj

        return {**params_from_context, **values_from_parameters}

    def __get(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> __T:
        """Create the real instances of dependencies. Additional dependencies they may have will be lazily created."""
        object_type_id = _ContainerObjectIdentifier(klass, qualifier)
        if object_type_id in self.__initialized_objects:
            return self.__initialized_objects[object_type_id]

        self.__assert_dependency_exists(klass, qualifier)
        class_to_initialize = klass
        if klass in self.__known_interfaces:  # noqa: SIM102
            if concrete_class := self.__get_concrete_class_from_interface_and_qualifier(klass, qualifier):
                class_to_initialize = concrete_class

        if self.__is_impl_known_from_factory(class_to_initialize):
            fn = self.__factory_functions[class_to_initialize]
            instance = fn(**self.__callable_get_params_to_inject(fn))
        else:
            instance = class_to_initialize(**self.__callable_get_params_to_inject(klass.__init__, class_to_initialize))

        self.__initialized_objects[_ContainerObjectIdentifier(class_to_initialize, qualifier)] = instance

        return instance

    def __get_container_dependency_or_param(self, parameter: Parameter) -> Any:
        default = parameter.default
        # Dealing with parameter, return the value as we cannot proxy int str etc.
        if isinstance(default, ParameterWrapper):
            return self.params.get(default.param)

        return self.__initialize_container_proxy_object_from_parameter(parameter)

    def __initialize_container_proxy_object_from_parameter(self, parameter: Parameter) -> Any:
        if parameter.annotation is Parameter.empty:
            return None

        default_val = parameter.default
        annotated_type = parameter.annotation

        if self.__is_impl_known_from_factory(annotated_type):
            return self.__get_proxy_object(annotated_type, None)

        qualifier_value = default_val.qualifier if isinstance(default_val, ContainerProxyQualifier) else None

        if self.__is_interface_known(annotated_type):
            concrete_class = self.__get_concrete_class_from_interface_and_qualifier(annotated_type, qualifier_value)
            return self.__get_proxy_object(concrete_class, qualifier_value)

        if self.__is_impl_known(annotated_type):
            self.__assert_qualifier_is_valid_if_impl_known(annotated_type, qualifier_value)
            return self.__get_proxy_object(annotated_type, qualifier_value)

        # When injecting dependencies and a qualifier is used, throw if it's being used on an unknown type.
        # This prevents the default value from being used by the runtime.
        # We don't actually want that to happen as the value is used only for hinting the container
        # and all values should be supplied.
        if qualifier_value:
            msg = f"Cannot use qualifier {qualifier_value} on a type that is not managed by the container."
            raise ValueError(msg)

        return None

    def __get_proxy_object(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> ContainerProxy:
        return ContainerProxy(lambda: self.__get(klass, qualifier))

    def __get_concrete_class_from_interface_and_qualifier(
        self,
        klass: type[__T],
        qualifier: ContainerProxyQualifierValue,
    ) -> type[__T]:
        concrete_classes = self.__known_interfaces.get(klass, {})

        if qualifier in concrete_classes:
            return concrete_classes[qualifier]

        # We have to raise here otherwise if we have a default hinting the qualifier for an unknown type
        # which will result in the value of the parameter being ContainerProxyQualifier.
        msg = (
            f"Cannot instantiate concrete class for {klass} as qualifier '{qualifier}' is unknown. "
            f"Available qualifiers: {set(concrete_classes.keys())}"
        )
        raise ValueError(msg)

    def __is_interface_known_with_valid_qualifier(
        self,
        klass: type[__T],
        qualifier: ContainerProxyQualifierValue,
    ) -> bool:
        return klass in self.__known_interfaces and qualifier in self.__known_interfaces[klass]

    def __is_impl_known(self, klass: type[__T]) -> bool:
        return klass in self.__known_impls

    def __is_interface_known(self, klass: type[__T]) -> bool:
        return klass in self.__known_interfaces

    def __is_impl_known_from_factory(self, klass: type[__T]) -> bool:
        return klass in self.__factory_functions

    def __is_impl_with_qualifier_known(self, klass: type[__T], qualifier_value: ContainerProxyQualifierValue) -> bool:
        return klass in self.__known_impls and qualifier_value in self.__known_impls[klass]

    def __is_dependency_known(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> bool:
        is_known_impl = self.__is_impl_with_qualifier_known(klass, qualifier)
        is_known_intf = self.__is_interface_known_with_valid_qualifier(klass, qualifier)
        is_known_from_factory = self.__is_impl_known_from_factory(klass)

        return is_known_impl or is_known_intf or is_known_from_factory

    def __assert_dependency_exists(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> None:
        """Assert that there exists an impl with that qualifier or an interface with an impl and the same qualifier."""
        if not self.__is_dependency_known(klass, qualifier):
            msg = f"Cannot wire unknown class {klass}. Use @Container.{{register,abstract}} to enable autowiring"
            raise ValueError(msg)

    def __assert_qualifier_is_valid_if_impl_known(
        self,
        klass: type[__T],
        qualifier_value: ContainerProxyQualifierValue,
    ) -> None:
        if not self.__is_impl_with_qualifier_known(klass, qualifier_value):
            msg = (
                f"Cannot instantiate concrete class for {klass} as qualifier '{qualifier_value}' is unknown. "
                f"Available qualifiers: {self.__known_impls[klass]}"
            )
            raise ValueError(msg)
