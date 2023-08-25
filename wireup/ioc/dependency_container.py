from __future__ import annotations

import asyncio
import functools
import importlib
import inspect
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from .container_util import (
    ContainerProxy,
    ContainerProxyQualifier,
    ContainerProxyQualifierValue,
    DependencyInitializationContext,
    ParameterWrapper,
    TemplatedString,
    _ContainerObjectIdentifier,
)
from .util import find_classes_in_module

if TYPE_CHECKING:
    from inspect import Parameter
    from types import ModuleType

    from .parameter import ParameterBag

__T = TypeVar("__T")


class DependencyContainer:
    """Container registry containing all the necessary information for initializing registered classes.

    Objects instantiated by the container are lazily loaded and initialized only on first use.

    Provides the following decorators: register, abstract and autowire. Use register on concrete classes
    which are to be injected from the container. Abstract classes are to be used as interfaces and will not be
    injected directly, rather concrete classes which implement them will be injected instead.

    Use autowire decorator on methods where dependency injection must be performed.
    To enable parameter injection use default values for parameters in conjunction with the wire method.

    Note: Fastapi users MUST use ` = .wire()` method without arguments when injecting dependencies.
    """

    def __init__(self, parameter_bag: ParameterBag) -> None:
        """:param parameter_bag: ParameterBag instance holding parameter information."""
        self.__known_interfaces: dict[type[__T], dict[str, type[__T]]] = {}
        self.__known_classes: set[_ContainerObjectIdentifier] = set()
        self.__initialized_objects: dict[_ContainerObjectIdentifier, object] = {}
        self.params: ParameterBag = parameter_bag
        self.initialization_context = DependencyInitializationContext()

    def wire(
        self,
        *,
        param: str | None = None,
        expr: str | None = None,
        qualifier: ContainerProxyQualifierValue = None,
    ) -> Callable[..., Any] | ParameterWrapper | ContainerProxy | Any:
        """Inject resources from the container to constructor or autowired method arguments.

        The arguments are exclusive and only one of them must be used at any time.

        :param param: Allows injecting a given parameter by name
        :param expr: Interpolate the templated string.
        Parameters inside ${} will be replaced with their corresponding value

        :param qualifier: Qualify which implementation to bind when there are multiple components
        implementing an interface that is registered in the container via @abstract.
        Can be used in conjunction with dep.
        """
        if param:
            return ParameterWrapper(param)

        if expr:
            return ParameterWrapper(TemplatedString(expr))

        if qualifier:
            return ContainerProxyQualifier(qualifier)

        try:
            # Allow fastapi users to do .get() without any params
            # It is meant to be used as a default value in where Depends() is expected
            return importlib.import_module("fastapi").Depends(lambda: None)
        except ModuleNotFoundError as e:
            msg = "One of param, expr or qualifier must be set"
            raise ValueError(msg) from e

    def get(self, klass: type[__T], qualifier: ContainerProxyQualifierValue = None) -> __T:
        """Get an instance of the requested type. If there is already an initialized instance, that will be returned.

        :param qualifier: Qualifier for the class if it was registered with one. If a type has only one qualifier
        then that will be returned if this parameter is left empty.
        :param klass: Class of the component already registered in the container.
        :return:
        """
        self.__assert_class_is_registered(klass, qualifier)

        return self.__get_proxy_object(_ContainerObjectIdentifier(klass, qualifier))

    def abstract(self, klass: type[__T]) -> type[__T]:
        """Register a type as an interface.

        This type cannot be initialized directly and one of the components implementing this will be injected instead.
        """
        self.__known_interfaces[klass] = defaultdict()

        return klass

    def register(self, klass: type[__T] | None = None, *, qualifier: ContainerProxyQualifierValue = None) -> type[__T]:
        """Register a component in the container.

        Use @register without parameters on a class
        or with a single parameter @register(qualifier=name) to register this with a given name
        when there are multiple implementations of the interface this implements.

        The container stores all necessary metadata for this class and the underlying class remains unmodified.
        """
        # Allow register to be used either with or without arguments
        if klass is None:

            def decorated(inner_class: type[__T]) -> type[__T]:
                return self.__register_inner(inner_class, qualifier)

            return decorated

        return self.__register_inner(klass, qualifier)

    def autowire(self, fn: Callable) -> Callable:
        """Automatically inject resources from the container to the decorated methods.

        Any arguments which the container does not know about will be ignored
        so that another decorator or framework can supply their values.
        This decorator can be used on both async and blocking methods.

        * Classes will be automatically injected.
        * Parameters need a value to be provided via .wire(param=) or .wire(expr=) using a default value.
        * When injecting an interface for which there are multiple implementations you need to supply a qualifier
          via .wire(qualifier=) using a default value.

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
        """Register all modules inside a given package.

        Useful when your components reside in one place, and you'd like to avoid having to @register each of them.
        Alternatively this can be used if you wish to use the library without having to rely on decorators.

        See Also: self.initialization_context to wire parameters without having to use a default value.

        :param module: The package name to recursively search for classes.
        :param pattern: A pattern that will be fed to fnmatch to determine if a class will be registered or not.
        """
        for klass in find_classes_in_module(module, pattern):
            self.register(klass)

    def __register_inner(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> type[__T]:
        object_type_id = _ContainerObjectIdentifier(klass, qualifier)

        if self.__is_class_known(klass, qualifier):
            msg = "Class already registered in container."
            raise ValueError(msg)

        if klass.__base__ in self.__known_interfaces:
            if qualifier in self.__known_interfaces[klass.__base__]:
                msg = (
                    f"Cannot register concrete class {klass} for {klass.__base__} "
                    f"with qualifier '{qualifier}' as it already exists"
                )
                raise ValueError(msg)

            self.__known_interfaces[klass.__base__][qualifier] = klass

        self.__known_classes.add(object_type_id)

        return klass

    def __autowire_inner(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return fn(*args, **{**kwargs, **self.__callable_get_params_to_inject(fn)})

    def __callable_get_params_to_inject(self, fn: Callable[..., Any], klass: type[__T] | None = None) -> dict:
        params_from_context = (
            {
                name: self.params.get(wrapper.param)
                for name, wrapper in self.initialization_context.context[klass].items()
            }
            if klass
            else {}
        )

        values_from_parameters = {
            name: self.__initialize_container_proxy_object_from_parameter(parameter)
            for name, parameter in inspect.signature(fn).parameters.items()
        }

        return {**params_from_context, **{k: v for k, v in values_from_parameters.items() if v}}

    def __get(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> __T:
        object_type_id = _ContainerObjectIdentifier(klass, qualifier)

        if object_type_id in self.__initialized_objects:
            return self.__initialized_objects[object_type_id]

        self.__assert_class_is_registered(klass, qualifier)

        if klass in self.__known_interfaces and qualifier:
            concrete_class = self.__get_concrete_class_from_qualifier(klass, qualifier)
            if concrete_class:
                return self.get(concrete_class, qualifier)

        instance = klass(**self.__callable_get_params_to_inject(klass.__init__, klass))
        self.__initialized_objects[object_type_id] = instance

        return instance

    def __is_class_known(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> bool:
        is_known_class = _ContainerObjectIdentifier(klass, qualifier) in self.__known_classes
        is_known_interface = klass in self.__known_interfaces and qualifier in self.__known_interfaces[klass]

        return is_known_class or is_known_interface

    def __assert_class_is_registered(self, klass: type[__T], qualifier: ContainerProxyQualifierValue) -> None:
        """Verify that either the class is a known dependency with this identifier or the type is abstract."""
        if not self.__is_class_known(klass, qualifier):
            msg = f"Cannot wire unknown class {klass}. Use @Container.{{register,abstract}} to enable autowiring"
            raise ValueError(msg)

    def __initialize_container_proxy_object_from_parameter(self, parameter: Parameter) -> Any:
        default = parameter.default

        # Dealing with parameter, return the value as we cannot proxy int str etc.
        if isinstance(default, ParameterWrapper):
            return self.params.get(default.param)

        # When injecting values and a qualifier is used, throw if it's being used on an unknown type.
        # This prevents the default value from being used by the runtime.
        # We don't actually want that to happen as the value is used only for hinting the container
        # and all values should be supplied.
        qualifier_value = default.qualifier if isinstance(default, ContainerProxyQualifier) else None
        class_to_instantiate = (
            self.__get_concrete_class_from_qualifier(parameter.annotation, qualifier_value)
            if qualifier_value
            else parameter.annotation
        )

        if self.__is_class_known(class_to_instantiate, qualifier_value):
            return self.__get_proxy_object(_ContainerObjectIdentifier(class_to_instantiate, qualifier_value))

        return None

    def __get_proxy_object(self, obj_id: _ContainerObjectIdentifier) -> ContainerProxy:
        return ContainerProxy(lambda: self.__get(obj_id.class_type, obj_id.qualifier))

    def __get_concrete_class_from_qualifier(
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
