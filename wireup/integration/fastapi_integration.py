from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

from wireup import DependencyContainer, container, initialize_container
from wireup.integration import _BaseIntegration
from wireup.integration.util import is_view_using_container

if TYPE_CHECKING:
    from collections.abc import Hashable
    from types import ModuleType

    from fastapi import FastAPI

    from wireup.ioc.dependency_container import DependencyContainer


def _autowire_views(container: DependencyContainer, app: FastAPI) -> None:
    for route in app.routes:
        if (
            isinstance(route, APIRoute)
            and route.dependant.call
            and is_view_using_container(container, route.dependant.call)
        ):
            route.dependant.call = container.autowire(route.dependant.call)


def wireup_init_fastapi_integration(
    app: FastAPI,
    service_modules: list[ModuleType],
    dependency_container: DependencyContainer = container,
) -> None:
    """Integrate wireup with a fastapi application.

    This must be called once all views have been registered.
     Decorates all views where container objects are being used making
     the `@container.autowire` decorator no longer needed.

    :param app: The application instance
    :param service_modules: A list of python modules where application services reside. These will be loaded to trigger
    container registrations.
    :param dependency_container: The instance of the dependency container.
    The default wireup singleton will be used when this is unset.
    This will be a noop and have no performance penalty for views which do not use the container.
    """
    initialize_container(dependency_container, service_modules=service_modules)
    _autowire_views(dependency_container, app)


class FastApiIntegration(_BaseIntegration):
    def __init__(self, container: DependencyContainer, app: FastAPI) -> None:
        super().__init__(container)
        self.app = app

    def get_key(self) -> Hashable:
        return self.app

    def setup(self) -> None:
        _autowire_views(self.container, self.app)

    def get_parameters(self) -> dict[str, Any]:
        return {}
