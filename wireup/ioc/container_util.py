from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from inspect import Parameter, Signature
from types import MappingProxyType
from typing import Any, Callable, Optional, TypeVar, Union


@dataclass(frozen=True)
class TemplatedString:
    """Wrapper for strings which contain values that must be interpolated by the parameter bag.

    Use this with the special ${param_name} syntax to reference a parameter in a string similar to python f-string.
    Strings in .wire(expr="") calls are automatically wrapped.
    """

    value: str


ParameterReference = Union[str, TemplatedString]


@dataclass(frozen=True)
class ParameterWrapper:
    """Wrapper for parameter values. This indicates to the container registry that this argument is a parameter."""

    param: ParameterReference


ContainerProxyQualifierValue = Optional[str]


@dataclass(frozen=True)
class ContainerProxyQualifier:
    """Hint the container registry which dependency to load when there are multiple ones registered with the same type.

    Use in case of interfaces where there are multiple dependencies that inherit it, but the type of the parameter
    is that of the base class acting as an interface.
    """

    qualifier: ContainerProxyQualifierValue


class DependencyInitializationContext:
    """Contains information about initializing a particular dependency.

    Use in cases where you want to avoid using `.wire` calls for parameter injection.
    """

    def __init__(self) -> None:
        """Initialize an empty context."""
        self.context: dict[type, dict[str, ParameterWrapper]] = defaultdict(dict)

    def add_param(self, klass: type, argument_name: str, parameter_ref: ParameterReference) -> None:
        """Add a parameter to the context.

        :param klass: The class type which this parameter belongs to
        :param argument_name: The name of the parameter in the klass initializer.
        :param parameter_ref: A reference to a parameter in the bag.
        """
        self.context[klass][argument_name] = ParameterWrapper(parameter_ref)

    def update(self, klass: type, params: dict[str, ParameterReference]) -> None:
        """Merge the context information for a particular type.

        Updates the context with the values from the new dictionary. Parameters from the argument will overwrite
        any existing ones with the same name. Behaves the same as the standard dict.update. Parameter values
        will be wrapped in ParameterWrapper.

        :param klass: The class type to be updated
        :param params: A dictionary of parameter references. Keys map to the parameter name and values
        contain references to parameters in the bag.
        """
        self.context[klass].update({k: ParameterWrapper(v) for k, v in params.items()})


class ContainerProxy:
    """A proxy object used by the container to achieve lazy loading.

    Contains a reference to the final initialized object and proxies all requests to the instance.
    """

    def __init__(self, instance_supplier: Callable) -> None:
        """Initialize a ContainerProxy.

        :param instance_supplier: A callable which takes no arguments and returns the object. Will be called to
        retrieve the actual instance when the objects' properties are first being accessed.
        """
        self.__supplier = instance_supplier
        self.__proxy_object = None

    def __getattr__(self, name: Any) -> Any:
        """Intercept object property access and forwards them to the proxied object.

        If the proxied object has not been initialized yet, a call to instance_supplier is made to retrieve it.

        :param name: Attribute name being accessed
        """
        if not self.__proxy_object:
            self.__proxy_object = self.__supplier()

        return getattr(self.__proxy_object, name)


__T = TypeVar("__T")


@dataclass(frozen=True, eq=True)
class _ContainerObjectIdentifier:
    """Identifies a dependency instance.

    Used to store and retrieve instances from the in-memory cache.
    """

    class_type: type[__T]
    qualifier: ContainerProxyQualifierValue


@dataclass(frozen=True)
class _ContainerClassMetadata:
    singleton: bool
    init_signature: Signature
