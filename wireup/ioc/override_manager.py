from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from wireup.ioc.types import ContainerProxyQualifierValue, ServiceOverride


class OverrideManager:
    """Enables overriding of services registered with the container."""

    def __init__(self, active_overrides: dict[tuple[type, ContainerProxyQualifierValue], Any]) -> None:
        self.__active_overrides = active_overrides

    def set(self, target: type, new: Any, qualifier: ContainerProxyQualifierValue = None) -> None:
        """Override the `target` service with `new`.

        Subsequent autowire calls to `target` will result in `new` being injected.

        :param target: The target service to override.
        :param qualifier: The qualifier of the service to override. Set this if service is registered
        with the qualifier parameter set to a value.
        :param new: The new object to be injected instead of `target`.
        """
        self.__active_overrides[target, qualifier] = new

    def delete(self, target: type, qualifier: ContainerProxyQualifierValue = None) -> None:
        """Clear active override for the `target` service."""
        if (target, qualifier) in self.__active_overrides:
            del self.__active_overrides[target, qualifier]

    def clear(self) -> None:
        """Clear all active service overrides."""
        self.__active_overrides.clear()

    @contextmanager
    def service(self, target: type, new: Any, qualifier: ContainerProxyQualifierValue = None) -> Iterator[None]:
        """Override the target service with new for the duration of the context manager.

        Subsequent autowire calls to `target` will result in `new` being injected.

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
        """Override the target service with new for the duration of the context manager.

        Identical behavior to `override` except supports overriding multiple services at a time.
        """
        try:
            for override in overrides:
                self.set(override.target, override.new, override.qualifier)
            yield
        finally:
            for override in overrides:
                self.delete(override.target, override.qualifier)
