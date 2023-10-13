from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Generic, TypeVar

from wireup.ioc.types import AnnotatedParameter, AutowireTarget, ParameterWrapper, ServiceLifetime

if TYPE_CHECKING:
    from collections.abc import Mapping

    from wireup import ParameterReference

__T = TypeVar("__T")


class InitializationContext(Generic[__T]):
    """The initialization context for registered targets. A map between an injection target and its dependencies.

    Container uses this to determine what to inject for each target.
    """

    __slots__ = ("__dependencies", "__dependencies_view", "__lifetime", "__lifetime_view")

    def __init__(self) -> None:
        """Create a new InitializationContext."""
        self.__dependencies: dict[AutowireTarget[__T], dict[str, AnnotatedParameter[__T]]] = {}
        self.__dependencies_view = MappingProxyType(self.__dependencies)

        self.__lifetime: dict[type[__T], ServiceLifetime] = {}
        self.__lifetime_view = MappingProxyType(self.__lifetime)

    @property
    def lifetime(self) -> Mapping[type[__T], ServiceLifetime]:
        """Return a read-only view of service lifetime mapping."""
        return self.__lifetime_view

    @property
    def dependencies(self) -> Mapping[AutowireTarget[__T], dict[str, AnnotatedParameter[__T]]]:
        """Return a read-only view of the dependency definitions."""
        return self.__dependencies_view

    def init(self, target: AutowireTarget[__T], lifetime: ServiceLifetime | None = None) -> bool:
        """Initialize the context for a particular target.

        Returns true on first call. If the target is already registered it returns False.
        """
        if target in self.__dependencies:
            return False

        self.__dependencies[target] = {}

        if isinstance(target, type) and lifetime is not None:
            self.__lifetime[target] = lifetime

        return True

    def put(self, target: AutowireTarget[__T], parameter_name: str, value: AnnotatedParameter[__T]) -> None:
        """Update the mapping of dependencies for a particular target.

        Registers a new dependency for the parameter in parameter_name.
        """
        self.__dependencies[target][parameter_name] = value

    def put_param(self, target: AutowireTarget[__T], argument_name: str, parameter_ref: ParameterReference) -> None:
        """Add a parameter to the context.

        :param target: The class type which this parameter belongs to
        :param argument_name: The name of the parameter in the klass initializer.
        :param parameter_ref: A reference to a parameter in the bag.
        """
        self.__dependencies[target][argument_name] = AnnotatedParameter(
            annotation=ParameterWrapper(parameter_ref),
        )

    def delete(self, target: AutowireTarget[__T], names_to_remove: set[str]) -> None:
        """Remove dependencies with names in `names_to_remove` from the given target."""
        self.__dependencies[target] = {k: v for k, v in self.__dependencies[target].items() if k not in names_to_remove}
