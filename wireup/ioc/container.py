import asyncio
import functools
import importlib
from collections import defaultdict
from inspect import Parameter
from typing import Any, Callable, Optional, Set, Type, TypeVar, Dict

from .container_util import (
    DependencyInitializationContext,
    ContainerProxy,
    ContainerProxyQualifier,
    ContainerParameterInitializationType,
    ParameterWrapper,
    TemplatedString,
)
from .parameter import ParameterBag
from .util import find_classes_in_package, get_class_parameter_type_hints, get_params_with_default_values

T = TypeVar("T")


class Container:
    def __init__(self, parameter_bag: ParameterBag) -> None:
        self.__known_interfaces: Dict[Type, Dict[str, Type]] = {}
        self.__known_classes: Set[Type] = set()
        self.params: ParameterBag = parameter_bag
        self.initialization_context = DependencyInitializationContext()

    @functools.cache
    def wire(
        self,
        *,
        param: Optional[str] = None,
        expr: Optional[str] = None,
        dep: Optional[Type[T]] = None,
        qualifier: Optional[str] = None,
    ) -> Callable[..., Any] | ParameterWrapper | ContainerProxy | Any:
        """
        Inject resources from the container to constructor or autowired method arguments.
        The arguments are exclusive and only one of them must be used at any time

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

        if dep:
            return ContainerProxy(lambda: self.__get(dep))

        if qualifier:
            return ContainerProxyQualifier(qualifier)

        try:
            # Allow fastapi users to do .get() without any params
            # It is meant to be used as a default value in where Depends() is expected
            return importlib.import_module("fastapi").Depends(lambda: None)
        except ModuleNotFoundError:
            raise Exception("One of param, expr, qualifier or dep must be set")

    def get(self, klass: Type[T]) -> T:
        """
        Get an instance of the requested type. If there is already an initialized instance, that will be returned.
        :param klass: Class of the component already registered in the container.
        :return:
        """
        self.__assert_class_is_known(klass)

        return self.wire(dep=klass)

    def abstract(self, klass: Type[T]) -> Type[T]:
        """
        Register a type as an interface. This type cannot be initialized directly and
        one of the components implementing this will be injected instead.
        """
        self.__known_interfaces[klass] = defaultdict()

        return klass

    def register(self, klass: Type[T] = None, *, qualifier: str = "") -> Type[T]:
        """
        Register a component in the container. Use @register without parameters on a class
        or with a single parameter @register(qualifier=name) to register this with a given name
        when there are multiple implementations of the interface this implements.

        The container stores all necessary metadata for this class and the underlying class remains unmodified.
        """
        # Allow register to be used either with or without arguments
        if klass is None:

            def decorated(inner_class: Type[T]) -> Type[T]:
                return self.__register_inner(inner_class, qualifier)

            return decorated

        return self.__register_inner(klass, "")

    def autowire(self, fn: Callable) -> Callable:
        """
        Automatically inject resources from the container to the decorated methods.
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
            async def async_inner(*args, **kwargs):
                return await self.__autowire_inner(fn, *args, **kwargs)

            return async_inner

        @functools.wraps(fn)
        def sync_inner(*args, **kwargs):
            return self.__autowire_inner(fn, *args, **kwargs)

        return sync_inner

    def register_all_in_module(self, package) -> None:
        """
        Register all modules inside a given package. Useful when your components reside in one place,
        and you'd like to avoid having to @register each of them.
        Alternatively this can be used if you wish to use the library without having to rely on decorators.

        See Also: self.initialization_context to wire parameters without having to use a default value.
        """
        for klass in find_classes_in_package(package):
            self.register(klass)

    def __register_inner(self, klass: Type[T], qualifier: str) -> Type[T]:
        if klass in self.__known_classes:
            raise ValueError("Class already registered in container.")

        if klass.__base__ in self.__known_interfaces:
            if qualifier in self.__known_interfaces[klass.__base__]:
                raise ValueError(
                    f"Cannot register concrete class {klass} for "
                    f"{klass.__base__} with qualifier '{qualifier}' as it already exists"
                )

            self.__known_interfaces[klass.__base__][qualifier] = klass

        self.__known_classes.add(klass)

        return klass

    def __autowire_inner(self, fn: Callable, *args, **kwargs) -> Any:
        return fn(*args, **{**kwargs, **self.__callable_get_params_to_inject(fn)})

    def __callable_get_params_to_inject(self, fn, klass: Type[T] = None):
        params_from_context = (
            {
                name: self.params.get(wrapper.param)
                for name, wrapper in self.initialization_context.context[klass].items()
            }
            if klass
            else {}
        )

        params_with_default_val_wrapper = {
            name: self.__initialize_from_default_value(parameter)
            for name, parameter in get_params_with_default_values(fn).items()
            if isinstance(parameter.default, ContainerParameterInitializationType)
        }

        dependencies = {
            name: self.wire(dep=t)
            for name, t in get_class_parameter_type_hints(fn).items()
            if t in self.__known_classes or t in self.__known_interfaces
        }

        return {**dependencies, **params_from_context, **params_with_default_val_wrapper}

    @functools.cache
    def __get(self, klass: Type[T], qualifier: Optional[str] = None) -> T:
        self.__assert_class_is_known(klass)

        if concrete_classes := self.__known_interfaces.get(klass):
            available_qualifiers = concrete_classes.keys()

            if qualifier is not None:
                if qualifier in available_qualifiers:
                    return self.__get(concrete_classes[qualifier])
                else:
                    raise ValueError(
                        f"Cannot instantiate concrete class for {klass} as qualifier '{qualifier}' is unknown. "
                        f"Available qualifiers: {available_qualifiers}"
                    )

            if len(available_qualifiers) == 1:
                concrete_class = next(iter(available_qualifiers))

                return self.__get(concrete_class)

            raise ValueError(
                f"Qualifier needed to instantiate concrete class for {klass}. "
                f"Available qualifiers: {available_qualifiers}"
            )

        return klass(**self.__callable_get_params_to_inject(klass.__init__, klass))

    def __assert_class_is_known(self, klass):
        if not (klass in self.__known_classes or klass in self.__known_interfaces):
            raise ValueError(f"Cannot wire unknown class {klass}. Use @Container.register to enable autowiring")

    def __initialize_from_default_value(self, parameter: Parameter):
        default = parameter.default

        if isinstance(default, ContainerProxyQualifier):
            return ContainerProxy(lambda: self.__get(parameter.annotation, default.qualifier))

        if isinstance(default, ParameterWrapper):
            return self.params.get(default.param)

        raise ValueError("Unknown Type to initialize from default value")
