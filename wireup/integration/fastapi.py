import functools
from contextvars import ContextVar
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute, APIWebSocketRoute

from wireup import ServiceLifetime
from wireup.decorators import make_inject_decorator
from wireup.errors import WireupError
from wireup.integration.util import is_view_using_container
from wireup.ioc.container.async_container import AsyncContainer
from wireup.ioc.container.scoped_container import ScopedAsyncContainer, enter_async_scope

current_request: ContextVar[Request] = ContextVar("wireup_fastapi_request")
current_ws_container: ContextVar[ScopedAsyncContainer] = ContextVar("wireup_fastapi_container")


async def _wireup_request_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    token = current_request.set(request)
    try:
        async with enter_async_scope(request.app.state.wireup_container) as scoped_container:
            request.state.wireup_container = scoped_container
            return await call_next(request)
    finally:
        current_request.reset(token)


def _fastapi_request_factory() -> Request:
    try:
        return current_request.get()
    except LookupError as e:
        msg = "fastapi.Request in wireup is only available during a request."
        raise WireupError(msg) from e


# We need to inject websocket routes separately as the regular fastapi middlewares work only for http.
def _inject_websocket_route(container: AsyncContainer, target: Callable[..., Any]) -> Callable[..., Any]:
    container._registry.target_init_context(target)

    @functools.wraps(target)
    async def _inner(*args: Any, **kwargs: Any) -> Any:
        async with enter_async_scope(container) as scoped_container:
            token = current_ws_container.set(scoped_container)
            res = await scoped_container._async_callable_get_params_to_inject(target)
            try:
                return await target(*args, **{**kwargs, **res.kwargs})
            finally:
                current_ws_container.reset(token)

    return _inner


def _inject_routes(container: AsyncContainer, app: FastAPI) -> None:
    inject_scoped = make_inject_decorator(container, get_request_container)

    for route in app.routes:
        if (
            isinstance(route, (APIRoute, APIWebSocketRoute))
            and route.dependant.call
            and is_view_using_container(container, route.dependant.call)
        ):
            target = route.dependant.call
            route.dependant.call = (
                inject_scoped(target) if isinstance(route, APIRoute) else _inject_websocket_route(container, target)
            )
            # Remove Request as a dependency from this target.
            # Let fastapi inject it instead and avoid duplicated work.
            container._registry.context.remove_dependency_type(target, Request)


def setup(container: AsyncContainer, app: FastAPI) -> None:
    """Integrate Wireup with FastAPI.

    This will automatically inject dependencies on FastAPI routers.
    """
    container._registry.register(_fastapi_request_factory, lifetime=ServiceLifetime.SCOPED)
    app.middleware("http")(_wireup_request_middleware)
    _inject_routes(container, app)
    app.state.wireup_container = container


def get_container(app: FastAPI) -> AsyncContainer:
    """Return the container associated with the given application."""
    return app.state.wireup_container


def get_request_container() -> ScopedAsyncContainer:
    """Return the container associated with the current request/websocket."""
    try:
        return current_request.get().state.wireup_container
    except LookupError:
        return current_ws_container.get()
