import contextlib
from contextvars import ContextVar
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Iterator,
    Tuple,
    Union,
)

from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.requests import HTTPConnection
from fastapi.routing import APIRoute, APIWebSocketRoute
from starlette.middleware.base import BaseHTTPMiddleware

from wireup import inject_from_container, service
from wireup.errors import WireupError
from wireup.integration.util import is_callable_using_wireup_dependencies
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer
from wireup.ioc.container.sync_container import ScopedSyncContainer
from wireup.ioc.types import AnyCallable
from wireup.ioc.validation import hide_annotated_names

current_request: ContextVar[HTTPConnection] = ContextVar("wireup_fastapi_request")


class WireupRoute(APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        hide_annotated_names(endpoint)
        super().__init__(path=path, endpoint=endpoint, **kwargs)


@service(lifetime="scoped")
def fastapi_request_factory() -> Request:
    """Provide the current FastAPI request as a dependency.

    Note that this requires the Wireup-FastAPI integration to be set up.
    """
    try:
        res = current_request.get()
        assert isinstance(res, Request)  # noqa: S101
        return res
    except LookupError as e:
        msg = "fastapi.Request in wireup is only available during a request."
        raise WireupError(msg) from e


@service(lifetime="scoped")
def fastapi_websocket_factory() -> WebSocket:
    """Provide the current FastAPI request as a dependency.

    Note that this requires the Wireup-FastAPI integration to be set up.
    """
    try:
        res = current_request.get()
        assert isinstance(res, WebSocket)  # noqa: S101
        return res
    except LookupError as e:
        msg = "fastapi.WebSocket in wireup is only available during a request."
        raise WireupError(msg) from e


# Warn: Make sure the logic evolves with the _request_middleware function.
async def _wireup_request_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    token = current_request.set(request)
    try:
        async with request.app.state.wireup_container.enter_scope() as scoped_container:
            request.state.wireup_container = scoped_container
            return await call_next(request)
    finally:
        current_request.reset(token)


def _inject_fastapi_route(
    *,
    container: AsyncContainer,
    target: AnyCallable,
    http_connection_param_name: str,
    is_http_connection_in_signature: bool,
    add_custom_middleware: bool,
) -> AnyCallable:
    # Warn: Make sure the logic evolves with the _wireup_request_middleware function.
    @contextlib.contextmanager
    def _request_middleware(
        scoped_container: Union[ScopedAsyncContainer, ScopedSyncContainer],
        _args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> Iterator[None]:
        request: HTTPConnection = kwargs[http_connection_param_name]
        request.state.wireup_container = scoped_container
        token = current_request.set(request)
        try:
            if not is_http_connection_in_signature:
                del kwargs[http_connection_param_name]
            yield
        finally:
            current_request.reset(token)

    return inject_from_container(container, middleware=_request_middleware if add_custom_middleware else None)(target)


def _inject_routes(container: AsyncContainer, app: FastAPI, *, add_custom_middleware: bool) -> None:
    for route in app.routes:
        if (
            isinstance(route, (APIRoute, APIWebSocketRoute))
            and route.dependant.call
            and is_callable_using_wireup_dependencies(route.dependant.call)
        ):
            if isinstance(route, APIRoute) and not add_custom_middleware:
                route.dependant.call = inject_from_container(container)(route.dependant.call)
                continue

            is_http_connection_in_signature = route.dependant.http_connection_param_name is not None

            if not route.dependant.http_connection_param_name:
                route.dependant.http_connection_param_name = "_fastapi_http_connection"

            route.dependant.call = _inject_fastapi_route(
                container=container,
                target=route.dependant.call,
                http_connection_param_name=route.dependant.http_connection_param_name,
                is_http_connection_in_signature=is_http_connection_in_signature,
                # For websocket routes we always add the middleware as the regular fastapi middleware
                # only applies to http requests.
                add_custom_middleware=add_custom_middleware or isinstance(route, APIWebSocketRoute),
            )


def _update_lifespan(container: AsyncContainer, app: FastAPI) -> None:
    old_lifespan = app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[Any]:
        async with old_lifespan(app) as state:
            yield state

        await container.close()

    app.router.lifespan_context = lifespan


def setup(container: AsyncContainer, app: FastAPI, *, expose_container_in_middleware: bool = True) -> None:
    """Integrate Wireup with FastAPI.

    Setup performs the following:
    * Injects dependencies into HTTP and WebSocket routes.
    * Creates a new container scope for each request, with a scoped lifetime matching the request duration.
    * Closes the Wireup container upon app shutdown using the lifespan context.

    For more details, visit: https://maldoinc.github.io/wireup/latest/integrations/fastapi/
    """
    if expose_container_in_middleware:
        app.add_middleware(BaseHTTPMiddleware, dispatch=_wireup_request_middleware)
    _update_lifespan(container, app)
    _inject_routes(container, app, add_custom_middleware=not expose_container_in_middleware)
    app.state.wireup_container = container


def get_app_container(app: FastAPI) -> AsyncContainer:
    """Return the container associated with the given FastAPI application."""
    return app.state.wireup_container


def get_request_container() -> ScopedAsyncContainer:
    """When inside a request, returns the scoped container instance handling the current request."""
    return current_request.get().state.wireup_container
