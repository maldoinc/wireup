from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple, Union

from typing_extensions import Literal

AnyCallable = Callable[..., Any]


class InjectableType:
    """Base type for anything that should be injected using annotation hints."""


@dataclass(frozen=True)
class TemplatedString:
    """Wrapper for strings which contain values that must be interpolated by the configuration store.

    Use this with the special ${config_value} syntax to reference a configuration in a formatted string.
    Strings in Inject(expr="") calls are automatically wrapped.
    """

    __slots__ = ("value",)

    value: str


ConfigurationReference = Union[str, TemplatedString]


@dataclass(frozen=True)
class ConfigInjectionRequest(InjectableType):
    """Flag to indicates to the registry that this argument is a configuration value."""

    __slots__ = ("config_key",)
    config_key: ConfigurationReference


Qualifier = Hashable
ContainerObjectIdentifier = Tuple[type, Optional[Qualifier]]


@dataclass(frozen=True)
class InjectableQualifier(InjectableType):
    """Hint the container registry which dependency to load when there are multiple ones registered with the same type.

    Use in case of interfaces where there are multiple dependencies that inherit it, but the type of the parameter
    is that of the base class acting as an interface.
    """

    __slots__ = ("qualifier",)

    qualifier: Qualifier | None


class EmptyContainerInjectionRequest(InjectableType):
    """Serves as hint for the container that it must always perform injection for this parameter.

    Instead of skipping, this would force it to throw if dependency is unknown
    """


InjectableLifetime = Literal["singleton", "scoped", "transient"]


class AnnotatedParameter:
    """Represent an annotated dependency parameter."""

    __slots__ = ("annotation", "is_parameter", "klass", "obj_id", "qualifier_value")

    def __init__(
        self,
        klass: type[Any],
        annotation: InjectableType | None = None,
    ) -> None:
        """Create a new AnnotatedParameter.

        If the annotation is a ContainerProxyQualifier, `qualifier_value` will be set to its value.

        :param klass: The type of the dependency
        :param annotation: Any annotation passed along. Such as Inject(config=...) calls
        """
        self.klass = klass
        self.annotation = annotation
        self.qualifier_value = self.annotation.qualifier if isinstance(self.annotation, InjectableQualifier) else None
        self.is_parameter = isinstance(self.annotation, ConfigInjectionRequest)
        self.obj_id = self.klass, self.qualifier_value

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
class InjectableOverride:
    """Data class to represent a injectable override. Target type will be replaced with the new type by the container."""

    target: type[Any]
    new: Any
    qualifier: Qualifier | None = None
