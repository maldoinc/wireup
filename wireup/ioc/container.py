from __future__ import annotations

import asyncio
import functools
import importlib
import inspect
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from .container_util import (
    ContainerParameterInitializationType,
    ContainerProxy,
    ContainerProxyQualifier,
    DependencyInitializationContext,
    ParameterWrapper,
    TemplatedString,
    _InitializedObjectIdentifier,
)
from .util import find_classes_in_module

if TYPE_CHECKING:
    from inspect import Parameter
    from types import ModuleType

    from .parameter import ParameterBag

T = TypeVar("T")


# TODO(mateli): Do we call this something registry?
class Container:
    """Container registry containing all the necessary information on initializing registered classes.

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
        self.__known_interfaces: dict[type[T], dict[str, type[T]]] = {}
        self.__known_classes: set[type[T]] = set()
        self.__initialized_objects: dict[_InitializedObjectIdentifier, object] = {}
        self.params: ParameterBag = parameter_bag
        self.initialization_context = DependencyInitializationContext()

    def wire(
        self,
        *,
        param: str | None = None,
        expr: str | None = None,
        dep: type[T] | None = None,
        qualifier: str | None = None,
    ) -> Callable[..., Any] | ParameterWrapper | ContainerProxy | Any:
        """Inject resources from the container to constructor or autowired method arguments.

        The arguments are exclusive and only one of them must be used at any time.

        :param param: Allows injecting a given parameter by name
        :param expr: Interpolate the templated string.
        Parameters inside ${} will be replaced with their corresponding value

        :param dep: Inject a component given a class name. Prefer type-hinting parameters instead
        :param qualifier: Qualify which implementation to bind when there are multiple components
        implementing an interface that is registered in the container via @abstract.
        :return:
        """
        if param:
            return ParameterWrapper(param)

        if expr:
            return ParameterWrapper(TemplatedString(expr))

        # TODO(mateli): Allow dep and qualifier to be used together
        if dep:
            return ContainerProxy(lambda: self.__get(dep))

        if qualifier:
            return ContainerProxyQualifier(qualifier)

        try:
            # Allow fastapi users to do .get() without any params
            # It is meant to be used as a default value in where Depends() is expected
            return importlib.import_module("fastapi").Depends(lambda: None)
        except ModuleNotFoundError as e:
            msg = "One of param, expr, qualifier or dep must be set"
            raise ValueError(msg) from e

    def get(self, klass: type[T]) -> T:
        """Get an instance of the requested type. If there is already an initialized instance, that will be returned.

        :param klass: Class of the component already registered in the container.
        :return:
        """
        self.__assert_class_is_known(klass)

        return self.wire(dep=klass)

    def abstract(self, klass: type[T]) -> type[T]:
        """Register a type as an interface.

        This type cannot be initialized directly and one of the components implementing this will be injected instead.
        """
        self.__known_interfaces[klass] = defaultdict()

        return klass

    def register(self, klass: type[T] | None = None, *, qualifier: str = "") -> type[T]:
        """Register a component in the container.

        Use @register without parameters on a class
        or with a single parameter @register(qualifier=name) to register this with a given name
        when there are multiple implementations of the interface this implements.

        The container stores all necessary metadata for this class and the underlying class remains unmodified.
        """
        # Allow register to be used either with or without arguments
        if klass is None:

            def decorated(inner_class: type[T]) -> type[T]:
                return self.__register_inner(inner_class, qualifier)

            return decorated

        return self.__register_inner(klass, "")

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

    def __register_inner(self, klass: type[T], qualifier: str) -> type[T]:
        if klass in self.__known_classes:
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

        self.__known_classes.add(klass)

        return klass

    def __autowire_inner(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return fn(*args, **{**kwargs, **self.__callable_get_params_to_inject(fn)})

    def __callable_get_params_to_inject(self, fn: Callable[..., Any], klass: type[T] | None = None) -> dict:
        params_from_context = (
            {
                name: self.params.get(wrapper.param)
                for name, wrapper in self.initialization_context.context[klass].items()
            }
            if klass
            else {}
        )

        params_with_default_val_wrapper = {}
        dependencies = {}

        for name, parameter in inspect.signature(fn).parameters.items():
            if isinstance(parameter.default, ContainerParameterInitializationType):
                params_with_default_val_wrapper[name] = self.__initialize_from_param_with_default_value(parameter)

            if parameter.annotation in self.__known_classes or parameter.annotation in self.__known_interfaces:
                dependencies[name] = self.wire(dep=parameter.annotation)

        return {**dependencies, **params_from_context, **params_with_default_val_wrapper}

    def __get(self, klass: type[T], qualifier: str | None = None) -> T:
        object_type_id = _InitializedObjectIdentifier(klass, qualifier)

        if object_type_id in self.__initialized_objects:
            return self.__initialized_objects[object_type_id]

        self.__assert_class_is_known(klass)

        concrete_classes: dict[str, type[T]] = self.__known_interfaces.get(klass)
        if concrete_classes:
            available_qualifiers: list[str] = list(concrete_classes.keys())

            if qualifier is not None:
                if qualifier in available_qualifiers:
                    return self.__get(concrete_classes[qualifier])

                msg = (
                    f"Cannot instantiate concrete class for {klass} as qualifier '{qualifier}' is unknown. "
                    f"Available qualifiers: {available_qualifiers}"
                )
                raise ValueError(msg)

            if len(available_qualifiers) == 1:
                return self.__get(klass, available_qualifiers[0])

            msg = (
                f"Qualifier needed to instantiate concrete class for {klass}. "
                f"Available qualifiers: {available_qualifiers}"
            )
            raise ValueError(msg)

        instance = klass(**self.__callable_get_params_to_inject(klass.__init__, klass))
        self.__initialized_objects[object_type_id] = instance

        return instance

    def __assert_class_is_known(self, klass: type[T]) -> None:
        if not (klass in self.__known_classes or klass in self.__known_interfaces):
            msg = f"Cannot wire unknown class {klass}. Use @Container.{{register,abstract}} to enable autowiring"
            raise ValueError(msg)

    def __initialize_from_param_with_default_value(self, parameter: Parameter) -> Any:
        default = parameter.default

        if isinstance(default, ContainerProxyQualifier):
            return ContainerProxy(lambda: self.__get(parameter.annotation, default.qualifier))

        if isinstance(default, ParameterWrapper):
            return self.params.get(default.param)

        msg = "Unknown Type to initialize from default value"
        raise ValueError(msg)
