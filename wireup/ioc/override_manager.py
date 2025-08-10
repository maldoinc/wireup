from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

from wireup.errors import UnknownOverrideRequestedError

if TYPE_CHECKING:
    from collections.abc import Callable

    from wireup.ioc.types import Qualifier, ServiceOverride


class OverrideManager:
    """Enables overriding of services registered with the container."""

    def __init__(
        self,
        active_overrides: dict[tuple[type, Qualifier], Any],
        is_valid_override: Callable[[type, Qualifier], bool],
    ) -> None:
        self.__is_valid_override = is_valid_override
        self.active_overrides = active_overrides

    def set(self, target: type, new: Any, qualifier: Qualifier | None = None) -> None:
        """Override the `target` service with `new`.

        Future requests to inject `target` will result in `new` being injected.

        :param target: The target service to override.
        :param qualifier: The qualifier of the service to override. Set this if service is registered
        with the qualifier parameter set to a value.
        :param new: The new object to be injected instead of `target`.
        """
        if not self.__is_valid_override(target, qualifier):
            raise UnknownOverrideRequestedError(klass=target, qualifier=qualifier)

        self.active_overrides[target, qualifier] = new

    def delete(self, target: type, qualifier: Qualifier | None = None) -> None:
        """Clear active override for the `target` service."""
        if (target, qualifier) in self.active_overrides:
            del self.active_overrides[target, qualifier]

    def clear(self) -> None:
        """Clear active service overrides."""
        self.active_overrides.clear()

    @contextmanager
    def service(self, target: type, new: Any, qualifier: Qualifier | None = None) -> Iterator[None]:
        """Override the `target` service with `new` for the duration of the context manager.

        Future requests to inject `target` will result in `new` being injected.

        :param target: The target service to override.
        :param qualifier: The qualifier of the service to override. Set this if service is registered
        with the qualifier parameter set to a value.
        :param new: The new object to be injected instead of `target`.
        """
        try:
            self.set(target, new, qualifier)
            yield
        finally:
            self.delete(target, qualifier)

    @contextmanager
    def services(self, overrides: list[ServiceOverride]) -> Iterator[None]:
        """Override a number of services with new for the duration of the context manager."""
        try:
            for override in overrides:
                self.set(override.target, override.new, override.qualifier)
            yield
        finally:
            for override in overrides:
                self.delete(override.target, override.qualifier)
