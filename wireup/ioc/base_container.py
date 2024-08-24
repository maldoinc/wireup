from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wireup.ioc.override_manager import OverrideManager

if TYPE_CHECKING:
    from wireup import ParameterBag
    from wireup.ioc.service_registry import ServiceRegistry
    from wireup.ioc.types import ContainerObjectIdentifier


class BaseContainer:
    """Base Container class providing core functionality."""

    __slots__ = ("_registry", "_params", "_override_mgr", "_overrides")

    def __init__(
        self,
        registry: ServiceRegistry,
        parameters: ParameterBag,
        overrides: dict[ContainerObjectIdentifier, Any],
    ) -> None:
        self._registry = registry
        self._params = parameters
        self._overrides = overrides
        self._override_mgr = OverrideManager(overrides, self._registry.is_type_with_qualifier_known)

    def is_type_known(self, klass: type) -> bool:
        """Given a class type return True if's registered in the container as a service or interface."""
        return self._registry.is_impl_known(klass) or self._registry.is_interface_known(klass)

    @property
    def override(self) -> OverrideManager:
        """Override registered container services with new values."""
        return self._override_mgr
