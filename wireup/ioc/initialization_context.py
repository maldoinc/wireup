from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from wireup.ioc.types import AnnotatedParameter, AutowireTarget, ServiceLifetime


class InitializationContext:
    """The initialization context for registered targets. A map between an injection target and its dependencies.

    Container uses this to determine what to inject for each target.
    """

    __slots__ = ("__dependencies", "__dependencies_view", "__lifetime", "__lifetime_view")

    def __init__(self) -> None:
        """Create a new InitializationContext."""
        self.__dependencies: dict[AutowireTarget, dict[str, AnnotatedParameter]] = {}
        self.__dependencies_view = MappingProxyType(self.__dependencies)

        self.__lifetime: dict[type, ServiceLifetime] = {}
        self.__lifetime_view = MappingProxyType(self.__lifetime)

    @property
    def lifetime(self) -> Mapping[type, ServiceLifetime]:
        """Read-only view of service lifetime mapping."""
        return self.__lifetime_view

    @property
    def dependencies(self) -> Mapping[AutowireTarget, dict[str, AnnotatedParameter]]:
        """Read-only view of the dependency definitions."""
        return self.__dependencies_view

    def init_target(self, target: AutowireTarget, lifetime: ServiceLifetime | None = None) -> bool:
        """Initialize the context for a particular target.

        Returns true on first call. If the target is already registered it returns False.
        """
        if target in self.__dependencies:
            return False

        self.__dependencies[target] = {}

        if isinstance(target, type) and lifetime is not None:
            self.__lifetime[target] = lifetime

        return True

    def add_dependency(self, target: AutowireTarget, parameter_name: str, value: AnnotatedParameter) -> None:
        """Update the mapping of dependencies for a particular target.

        Registers a new dependency for the parameter in parameter_name.
        Target must have been already initialized prior to calling this.
        """
        self.__dependencies[target][parameter_name] = value

    def remove_dependencies(self, target: AutowireTarget, names_to_remove: set[str]) -> None:
        """Remove dependencies with names in `names_to_remove` from the given target.

        Target must have been already initialized prior to calling this.
        """
        self.__dependencies[target] = {k: v for k, v in self.__dependencies[target].items() if k not in names_to_remove}
