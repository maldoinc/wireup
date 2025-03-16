import contextlib
import functools
from contextvars import ContextVar
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
)

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute, APIWebSocketRoute
from starlette.middleware.base import BaseHTTPMiddleware

from wireup._decorators import inject_from_container
from wireup.errors import WireupError
from wireup.integration.util import is_view_using_container
from wireup.ioc.container import assert_dependencies_valid
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer

current_request: ContextVar[Request] = ContextVar("wireup_fastapi_request")
current_ws_container: ContextVar[ScopedAsyncContainer] = ContextVar("wireup_fastapi_container")


async def _wireup_request_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    token = current_request.set(request)
    try:
        async with request.app.state.wireup_container.enter_scope() as scoped_container:
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
        async with container.enter_scope() as scoped_container:
            token = current_ws_container.set(scoped_container)
            res = await scoped_container._async_callable_get_params_to_inject(target)
            try:
                return await target(*args, **{**kwargs, **res.kwargs})
            finally:
                current_ws_container.reset(token)

    return _inner


def _inject_routes(container: AsyncContainer, app: FastAPI) -> None:
    inject_scoped = inject_from_container(container, get_request_container)

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


def _update_lifespan(container: AsyncContainer, app: FastAPI) -> None:
    old_lifespan = app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[Any]:
        async with old_lifespan(app) as state:
            yield state

        await container.close()

    app.router.lifespan_context = lifespan


def setup(container: AsyncContainer, app: FastAPI) -> None:
    """Integrate Wireup with FastAPI.

    This performs the following:
    * Inject dependencies in http and websocket routes.
    * Enter a new container scope per request. Scoped lifetime lasts as long as the request does.
    * Expose `fastapi.Request` as a Wireup scoped dependency.
    * Close the Wireup container on app shutdown via lifespan.

    See: https://maldoinc.github.io/wireup/latest/integrations/fastapi/

    Note that for lifespan events to trigger in the FastAPI test client you must use the client as a context manager.
    ```python
    @pytest.fixture()
    def client(app: FastAPI) -> Iterator[TestClient]:
        with TestClient(app) as client:
            yield client
    ```
    """
    container._registry.register(_fastapi_request_factory, lifetime="scoped")
    assert_dependencies_valid(container)
    _update_lifespan(container, app)

    app.add_middleware(BaseHTTPMiddleware, dispatch=_wireup_request_middleware)
    _inject_routes(container, app)
    app.state.wireup_container = container


def get_app_container(app: FastAPI) -> AsyncContainer:
    """Return the container associated with the given FastAPI application."""
    return app.state.wireup_container


def get_request_container() -> ScopedAsyncContainer:
    """When inside a request, returns the scoped container instance handling the current request."""
    try:
        return current_request.get().state.wireup_container
    except LookupError:
        return current_ws_container.get()
