from contextvars import ContextVar
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute

from wireup import DependencyContainer
from wireup.integration.util import is_view_using_container
from wireup.ioc.types import ServiceLifetime

current_request: ContextVar[Request] = ContextVar("wireup_fastapi_request")


async def _wireup_request_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    token = current_request.set(request)
    try:
        return await call_next(request)
    finally:
        current_request.reset(token)


def _fastapi_request_factory() -> Request:
    return current_request.get()


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
    container.register(_fastapi_request_factory, lifetime=ServiceLifetime.TRANSIENT)
    app.middleware("http")(_wireup_request_middleware)
    _autowire_views(container, app)
    app.state.wireup_container = container


def get_container(app: FastAPI) -> DependencyContainer:
    """Return the container associated with the given application."""
    return app.state.wireup_container
