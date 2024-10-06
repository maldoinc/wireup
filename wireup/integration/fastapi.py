from fastapi import FastAPI
from fastapi.routing import APIRoute

from wireup import DependencyContainer
from wireup.integration.util import is_view_using_container


def _autowire_views(container: DependencyContainer, app: FastAPI) -> None:
    for route in app.routes:
        if (
            isinstance(route, APIRoute)
            and route.dependant.call
            and is_view_using_container(container, route.dependant.call)
        ):
            route.dependant.call = container.autowire(route.dependant.call)


def setup(container: DependencyContainer, app: FastAPI) -> None:
    """Integrate Wireup with FastAPI.

    This will automatically inject dependencies on FastAPI routers.
    """
    _autowire_views(container, app)
    app.state.wireup_container = container


def get_container(app: FastAPI) -> DependencyContainer:
    """Return the container associated with the given application."""
    return app.state.wireup_container
