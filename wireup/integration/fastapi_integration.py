from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.routing import APIRoute

from wireup import DependencyContainer, container, warmup_container
from wireup.integration.util import is_view_using_container

if TYPE_CHECKING:
    from types import ModuleType

    from fastapi import FastAPI


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
    warmup_container(dependency_container, service_modules or [])

    for route in app.routes:
        if (
            isinstance(route, APIRoute)
            and route.dependant.call
            and is_view_using_container(dependency_container, route.dependant.call)
        ):
            route.dependant.call = dependency_container.autowire(route.endpoint)
