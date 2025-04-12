import contextlib
import functools
from contextvars import ContextVar
from typing import (
    Any,
    AsyncIterator,
    Callable,
)

from fastapi import FastAPI, Request, WebSocket
from fastapi.routing import APIRoute, APIWebSocketRoute
from starlette.types import ASGIApp, Receive, Scope, Send

from wireup import inject_from_container, service
from wireup.errors import WireupError
from wireup.integration.util import is_callable_using_wireup_dependencies
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer
from wireup.ioc.types import ParameterWrapper
from wireup.ioc.validation import get_valid_injection_annotated_parameters, hide_annotated_names

current_request_socket: ContextVar[Request | WebSocket] = ContextVar("wireup_fastapi_request")
current_ws_container: ContextVar[ScopedAsyncContainer] = ContextVar("wireup_fastapi_container")


class WireupRoute(APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        hide_annotated_names(endpoint)
        super().__init__(path=path, endpoint=endpoint, **kwargs)


class WireupMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            c = Request(scope)
        elif scope["type"] == "websocket":
            c = WebSocket(scope, receive, send)
        else:
            return await self.app(scope, receive, send)

        token = current_request_socket.set(c)

        try:
            async with c.app.state.wireup_container.enter_scope() as scoped_container:
                c.state.wireup_container = scoped_container
                return await self.app(scope, receive, send)
        finally:
            current_request_socket.reset(token)


@service(lifetime="scoped")
def fastapi_request_factory() -> Request:
    """Provide the current FastAPI request as a dependency.

    Note that this requires the Wireup-FastAPI integration to be set up.
    """
    try:
        c = current_request_socket.get()
        if not isinstance(c, Request):
            raise LookupError("Not a Request instance")
        return c
    except LookupError as e:
        msg = "fastapi.Request in wireup is only available during a request."
        raise WireupError(msg) from e


@service(lifetime="scoped")
def fastapi_websocket_factory() -> WebSocket:
    """Provide the current FastAPI websocket as a dependency.

    Note that this requires the Wireup-FastAPI integration to be set up.
    """
    try:
        c = current_request_socket.get()
        if not isinstance(c, WebSocket):
            raise LookupError("Not a WebSocket instance")
        return c
    except LookupError as e:
        msg = "fastapi.WebSocket in wireup is only available during a websocket connection."
        raise WireupError(msg) from e



# We need to inject websocket routes separately as the regular fastapi middlewares work only for http.
def _inject_websocket_route(container: AsyncContainer, target: Callable[..., Any]) -> Callable[..., Any]:
    names_to_inject = get_valid_injection_annotated_parameters(container, target)

    @functools.wraps(target)
    async def _inner(*args: Any, **kwargs: Any) -> Any:
        async with container.enter_scope() as scoped_container:
            token = current_ws_container.set(scoped_container)
            injected_names = {
                name: container.params.get(param.annotation.param)
                if isinstance(param.annotation, ParameterWrapper)
                else await scoped_container.get(param.klass, qualifier=param.qualifier_value)
                for name, param in names_to_inject.items()
                if param.annotation
            }

            try:
                return await target(*args, **{**kwargs, **injected_names})
            finally:
                current_ws_container.reset(token)

    return _inner


def _inject_routes(container: AsyncContainer, app: FastAPI) -> None:
    inject_scoped = inject_from_container(container, get_request_container)

    for route in app.routes:
        if (
            isinstance(route, (APIRoute, APIWebSocketRoute))
            and route.dependant.call
            and is_callable_using_wireup_dependencies(route.dependant.call)
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

    Setup performs the following:
    * Injects dependencies into HTTP and WebSocket routes.
    * Creates a new container scope for each request, with a scoped lifetime matching the request duration.
    * Closes the Wireup container upon app shutdown using the lifespan context.

    For more details, visit: https://maldoinc.github.io/wireup/latest/integrations/fastapi/

    Note: To trigger lifespan events in the FastAPI test client, use the client as a context manager.
    ```python
    @pytest.fixture()
    def client(app: FastAPI) -> Iterator[TestClient]:
        with TestClient(app) as client:
            yield client
    ```
    """
    _update_lifespan(container, app)
    app.add_middleware(WireupMiddleware)
    _inject_routes(container, app)
    app.state.wireup_container = container


def get_app_container(app: FastAPI) -> AsyncContainer:
    """Return the container associated with the given FastAPI application."""
    return app.state.wireup_container


def get_request_container() -> ScopedAsyncContainer:
    """When inside a request, returns the scoped container instance handling the current request."""
    try:
        return current_request_socket.get().state.wireup_container
    except LookupError:
        return current_ws_container.get()
