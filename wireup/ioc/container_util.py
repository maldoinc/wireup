from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Generic, Optional, Type, TypeVar, Union

__T = TypeVar("__T")
AnyCallable = Callable[..., Any]
AutowireTarget = Union[AnyCallable, Type[__T]]
"""Represents types that can be targets for autowiring.

This is any method where autowire decorator is used or any class which is registered in the container
where autowiring happens automatically.
"""


class InjectableType:
    """Base type for anything that should be injected using annotation hints."""


@dataclass(frozen=True)
class TemplatedString:
    """Wrapper for strings which contain values that must be interpolated by the parameter bag.

    Use this with the special ${param_name} syntax to reference a parameter in a string similar to python f-string.
    Strings in .wire(expr="") calls are automatically wrapped.
    """

    value: str


ParameterReference = Union[str, TemplatedString]


@dataclass(frozen=True)
class ParameterWrapper(InjectableType):
    """Wrapper for parameter values. This indicates to the container registry that this argument is a parameter."""

    param: ParameterReference


ContainerProxyQualifierValue = Optional[str]


@dataclass(frozen=True)
class ContainerProxyQualifier(InjectableType):
    """Hint the container registry which dependency to load when there are multiple ones registered with the same type.

    Use in case of interfaces where there are multiple dependencies that inherit it, but the type of the parameter
    is that of the base class acting as an interface.
    """

    qualifier: ContainerProxyQualifierValue


class ContainerProxy(Generic[__T]):
    """A proxy object used by the container to achieve lazy loading.

    Contains a reference to the final initialized object and proxies all requests to the instance.
    """

    def __init__(self, instance_supplier: Callable[[], __T]) -> None:
        """Initialize a ContainerProxy.

        :param instance_supplier: A callable which takes no arguments and returns the object. Will be called to
        retrieve the actual instance when the objects' properties are first being accessed.
        """
        self.__supplier = instance_supplier
        self.__proxy_object: __T | None = None

    def __getattr__(self, name: Any) -> Any:
        """Intercept object property access and forwards them to the proxied object.

        If the proxied object has not been initialized yet, a call to instance_supplier is made to retrieve it.

        :param name: Attribute name being accessed
        """
        if not self.__proxy_object:
            self.__proxy_object = self.__supplier()

        return getattr(self.__proxy_object, name)


class ContainerInjectionRequest(InjectableType):
    """Serves as hint for the container that it must always perform injection for this parameter.

    Instead of skipping, this would force it to throw if dependency is unknown
    """


class ServiceLifetime(Enum):
    """Determines the lifetime of a service."""

    SINGLETON = auto()
    """Singleton services are initialized once and reused throughout the lifetime of the container."""

    TRANSIENT = auto()
    """Transient services will have a fresh instance initialized on every injection."""
