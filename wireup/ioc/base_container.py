from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from wireup.errors import (
    UnknownQualifiedServiceRequestedError,
    UsageOfQualifierOnUnknownObjectError,
)
from wireup.ioc.override_manager import OverrideManager

if TYPE_CHECKING:
    from collections.abc import Callable

    from wireup import ParameterBag
    from wireup.ioc.service_registry import ServiceRegistry
    from wireup.ioc.types import ContainerObjectIdentifier, Qualifier

T = TypeVar("T")


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

    def _get_ctor(self, klass: type[T], qualifier: Qualifier | None) -> Callable[..., T] | None:
        if ctor := self._registry.factory_functions.get((klass, qualifier)):
            return ctor

        if self._registry.is_interface_known(klass):
            concrete_class = self._registry.interface_resolve_impl(klass, qualifier)
            return self._get_ctor(concrete_class, qualifier)

        if self._registry.is_impl_known(klass):
            if not self._registry.is_impl_with_qualifier_known(klass, qualifier):
                raise UnknownQualifiedServiceRequestedError(
                    klass,
                    qualifier,
                    self._registry.known_impls[klass],
                )
            return klass

        # When injecting dependencies and a qualifier is used, throw if it's being used on an unknown type.
        # This prevents the default value from being used by the runtime.
        # We don't actually want that to happen as the value is used only for hinting the container
        # and all values should be supplied.
        if qualifier:
            raise UsageOfQualifierOnUnknownObjectError(qualifier)

        return None
