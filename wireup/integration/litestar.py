import typing
from typing import Any, Type

from litestar import Litestar, Request, WebSocket

from wireup.integration._asgi_common import (
    current_request,
    get_app_container,
    get_request_container,
    inject,
    make_asgi_middleware,
    make_request_factory,
)
from wireup.ioc.container.async_container import AsyncContainer

__all__ = [
    "current_request",
    "get_app_container",
    "get_request_container",
    "inject",
    "request_factory",
    "websocket_factory",
]


def litestar_type_normalizer(type_: Type[Any]) -> Type[Any]:
    """Normalize litestar's generic Request and WebSocket types to their origin types.

    This allows injecting Request with generic types and have it resolve to the same instance as the raw type.
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


request_factory = make_request_factory(Request)
websocket_factory = make_request_factory(WebSocket)
_wireup_middleware = make_asgi_middleware(Request, WebSocket)


def setup(container: AsyncContainer, app: Litestar) -> None:
    """Integrate Wireup with a Litestar application.

    This sets up the application to use Wireup's dependency injection system.
    It also closes the container on shutdown for proper resource cleanup of singleton generator factories.
    """
    app.state.wireup_container = container
    app.on_shutdown.append(container.close)
    app.asgi_handler = _wireup_middleware(app.asgi_handler)
