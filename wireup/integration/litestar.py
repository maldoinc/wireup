import typing
from contextvars import ContextVar
from typing import Any, Type

from litestar import Litestar, Request, WebSocket
from litestar.connection.base import ASGIConnection
from litestar.types import ASGIApp, Receive, Scope, Send

from wireup._annotations import service
from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer

current_request: ContextVar[ASGIConnection[Any, Any, Any, Any]] = ContextVar("wireup_litestar_request")


def litestar_type_normalizer(type_: Type[Any]) -> Type[Any]:
    """Normalize litestar's generic Request and WebSocket types to their origin types.

    This allows users to inject Request[Any, Any, Any] and have it resolve to the same
    factory as the non-generic Request type.
    """
    origin_type = typing.get_origin(type_) or type_
    if (
        hasattr(origin_type, "__module__")
        and hasattr(origin_type, "__name__")
        and origin_type.__module__ in ("litestar.connection.request", "litestar.connection.websocket")
        and origin_type.__name__ in ("Request", "WebSocket")
    ):
        return origin_type
    return type_


@service(lifetime="scoped")
def request_factory() -> Request:  # type: ignore[reportMissingTypeArgument]
    """Provide the current request as a dependency."""
    msg = "Request in Wireup is only available during a request."
    try:
        res = current_request.get()
        if not isinstance(res, Request):
            raise WireupError(msg)

        return res
    except LookupError as e:
        raise WireupError(msg) from e


@service(lifetime="scoped")
def websocket_factory() -> WebSocket:  # type: ignore[reportMissingTypeArgument]
    """Provide the current WebSocket as a dependency."""
    msg = "WebSocket in Wireup is only available in a websocket connection."
    try:
        res = current_request.get()
        if not isinstance(res, WebSocket):
            raise WireupError(msg)

        return res
    except LookupError as e:
        raise WireupError(msg) from e


def _wireup_middleware(app: ASGIApp) -> ASGIApp:
    async def _middleware(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            return await app(scope, receive, send)

        if scope["type"] == "http":
            request: Request[Any, Any, Any] = Request(scope, receive, send)
        else:
            request: WebSocket[Any, Any, Any] = WebSocket(scope, receive, send)

        token = current_request.set(request)
        try:
            async with request.app.state.wireup_container.enter_scope() as scoped_container:
                request.state.wireup_container = scoped_container
                await app(scope, receive, send)
        finally:
            current_request.reset(token)

    return _middleware


def setup(container: AsyncContainer, app: Litestar) -> None:
    """Integrate Wireup with a Litestar application.

    This sets up the application to use Wireup's dependency injection system.
    It also closes the container on shutdown for proper resource cleanup of singleton generator factories.
    """
    app.state.wireup_container = container
    app.on_shutdown.append(container.close)
    app.asgi_handler = _wireup_middleware(app.asgi_handler)


def get_app_container(app: Litestar) -> AsyncContainer:
    """Return the container associated with the given application.

    This is the instance created via `wireup.create_async_container`.
    Use this when you need the container outside of the request context lifecycle.
    """
    return app.state.wireup_container


def get_request_container() -> ScopedAsyncContainer:
    """When inside a request, returns the scoped container instance handling the current request.

    This is what you almost always want. It has all the information the app container has in addition
    to data specific to the current request.
    """
    return current_request.get().state.wireup_container


inject = inject_from_container_unchecked(get_request_container, hide_wireup_params=True)
