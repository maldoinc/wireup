from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from wireup.ioc.types import ContainerProxyQualifierValue, ServiceOverride


class OverrideManager:
    def __init__(self, active_overrides: dict[(type, ContainerProxyQualifierValue), Any]):
        self.__active_overrides = active_overrides

    def set(self, target: type, new: Any, qualifier: ContainerProxyQualifierValue = None):
        self.__active_overrides[target, qualifier] = new

    def delete(self, target: type, qualifier: ContainerProxyQualifierValue = None):
        if (target, qualifier) in self.__active_overrides:
            del self.__active_overrides[target, qualifier]

    @contextmanager
    def service(self, target: type, new: Any, qualifier: ContainerProxyQualifierValue = None) -> Iterator[None]:
        """Override the target service with new for the duration of the context manager."""
        try:
            self.set(target, new, qualifier)
            yield
        finally:
            self.delete(target, qualifier)

    @contextmanager
    def services(self, overrides: list[ServiceOverride]) -> Iterator[None]:
        """Override the target service with new for the duration of the context manager."""
        try:
            for override in overrides:
                self.set(override.target, override.new, override.qualifier)
            yield
        finally:
            for override in overrides:
                self.delete(override.target, override.qualifier)
