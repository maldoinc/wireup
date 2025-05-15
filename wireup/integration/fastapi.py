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
        return current_request.get()  # type:ignore[return-value]
    except LookupError as e:
        msg = "fastapi.Request in wireup is only available during a request."
        raise WireupError(msg) from e


@service(lifetime="scoped")
def fastapi_websocket_factory() -> WebSocket:
    """Provide the current FastAPI WebSocket as a dependency.

    Note that this requires the Wireup-FastAPI integration to be set up.
    """
    try:
        return current_request.get()  # type: ignore[return-value]
    except LookupError as e:
        msg = "fastapi.WebSocket in wireup is only available during a request."
        raise WireupError(msg) from e


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
    remove_http_connection_from_arguments: bool,
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
            if remove_http_connection_from_arguments:
                del kwargs[http_connection_param_name]
            yield
        finally:
            current_request.reset(token)

    # If no scoped_container_supplier is passed, inject_from_container will enter one for us.
    # However we need to pass the custom middleware to set the request context variable.
    return inject_from_container(container, middleware=_request_middleware if add_custom_middleware else None)(target)


def _inject_routes(container: AsyncContainer, app: FastAPI, *, add_custom_middleware: bool) -> None:
    for route in app.routes:
        if not (isinstance(route, (APIRoute, APIWebSocketRoute)) and route.dependant.call):
            continue

        # If the setup has been done with expose_container_in_middleware=True,
        # the request context variable is already set in the middleware.
        # and we can get the scoped container from the request.
        if isinstance(route, APIRoute) and not add_custom_middleware:
            route.dependant.call = inject_from_container(container, get_request_container)(route.dependant.call)
            continue

        is_http_connection_in_signature = route.dependant.http_connection_param_name is not None

        # Setting http_connection_param_name forces FastAPI to pass the current HTTPConnection
        # to the route handler regardless of whether it was in the signature.
        # It is then extracted in the inject_from_container middleware to set the relevant context variable.
        if not route.dependant.http_connection_param_name:
            route.dependant.http_connection_param_name = "_fastapi_http_connection"

        # This is now either a websocket route or an APIRoute but set up was called
        # with expose_container_in_middleware=False.
        # In this case we need to pass the wireup middleware inject_from_container to set the request context variable.
        route.dependant.call = _inject_fastapi_route(
            container=container,
            target=route.dependant.call,
            http_connection_param_name=route.dependant.http_connection_param_name,
            # If the HTTPConnection was not in the signature, it needs to be removed from the arguments
            # when calling the route handler.
            remove_http_connection_from_arguments=not is_http_connection_in_signature,
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

    :param container: An async container created via `wireup.create_async_container`.
    :param app: The FastAPI application to integrate with.
    :param expose_container_in_middleware: If True, the container is exposed in fastapi middleware.
    Note, for this to work correctly, there should be no more middleware added after the call to this function.

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
