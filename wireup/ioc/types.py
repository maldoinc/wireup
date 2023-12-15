from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Optional, Union

AnyCallable = Callable[..., Any]
AutowireTarget = Union[AnyCallable, type]
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

    __slots__ = ("value",)

    value: str


ParameterReference = Union[str, TemplatedString]


@dataclass(frozen=True)
class ParameterWrapper(InjectableType):
    """Wrapper for parameter values. This indicates to the container registry that this argument is a parameter."""

    __slots__ = ("param",)
    param: ParameterReference


ContainerProxyQualifierValue = Optional[Any]


@dataclass(frozen=True)
class ContainerProxyQualifier(InjectableType):
    """Hint the container registry which dependency to load when there are multiple ones registered with the same type.

    Use in case of interfaces where there are multiple dependencies that inherit it, but the type of the parameter
    is that of the base class acting as an interface.
    """

    __slots__ = ("qualifier",)

    qualifier: ContainerProxyQualifierValue


class EmptyContainerInjectionRequest(InjectableType):
    """Serves as hint for the container that it must always perform injection for this parameter.

    Instead of skipping, this would force it to throw if dependency is unknown
    """


class ServiceLifetime(Enum):
    """Determines the lifetime of a service."""

    SINGLETON = auto()
    """Singleton services are initialized once and reused throughout the lifetime of the container."""

    TRANSIENT = auto()
    """Transient services will have a fresh instance initialized on every injection."""


class AnnotatedParameter:
    """Represent an annotated dependency parameter."""

    __slots__ = ("klass", "annotation", "qualifier_value", "is_parameter")

    def __init__(
        self,
        klass: type | None = None,
        annotation: Any | None = None,
    ) -> None:
        """Create a new AnnotatedParameter.

        If the annotation is a ContainerProxyQualifier, `qualifier_value` will be set to its value.

        :param klass: The type of the dependency
        :param annotation: Any annotation passed along. Such as Wire(param=...) calls
        """
        self.klass = klass
        self.annotation = annotation
        self.qualifier_value = (
            self.annotation.qualifier if isinstance(self.annotation, ContainerProxyQualifier) else None
        )
        self.is_parameter = isinstance(self.annotation, ParameterWrapper)

    def __eq__(self, other: object) -> bool:
        """Check if two things are equal."""
        return (
            isinstance(other, AnnotatedParameter)
            and self.klass == other.klass
            and self.annotation == other.annotation
            and self.qualifier_value == other.qualifier_value
            and self.is_parameter == other.is_parameter
        )

    def __hash__(self) -> int:
        """Hash things."""
        return hash((self.klass, self.annotation, self.qualifier_value, self.is_parameter))


@dataclass(frozen=True, eq=True)
class ServiceOverride:
    """Data class to represent a service override. Target type will be replaced with the new type by the container."""

    target: type
    qualifier: ContainerProxyQualifierValue
    new: Any
