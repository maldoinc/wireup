from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

if TYPE_CHECKING:
    from collections.abc import Hashable

    from wireup.ioc.dependency_container import DependencyContainer


class _BaseIntegration(abc.ABC):
    def __init__(self, container: DependencyContainer) -> None:
        self.container = container

    @abc.abstractmethod
    def setup(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_key(self) -> Hashable:
        raise NotImplementedError

    def get_parameters(self) -> dict[str, Any]:
        return {}


_integrations: WeakKeyDictionary[Hashable, _BaseIntegration] = WeakKeyDictionary()


def get_container(key: Hashable) -> DependencyContainer:
    """Return a running container associated with the given key."""
    return _integrations[key].container


def setup_integration(integration: _BaseIntegration) -> None:
    """Set up the given integration."""
    integration.setup()
    _integrations[integration.get_key()] = integration

    if integration_params := integration.get_parameters():
        integration.container.params.update(integration_params)
