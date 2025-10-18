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
