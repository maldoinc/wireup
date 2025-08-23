import contextlib
from typing import Any, AsyncIterator

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.websockets import WebSocket

from wireup.integration._asgi_common import (
    current_request,
    get_app_container,
    get_request_container,
    inject,
    make_asgi_middleware,
    make_request_factory,
)
from wireup.ioc.container.async_container import AsyncContainer

request_factory = make_request_factory(Request)
websocket_factory = make_request_factory(WebSocket)
wireup_asgi_middleware = make_asgi_middleware(Request, WebSocket)

__all__ = [
    "current_request",
    "get_app_container",
    "get_request_container",
    "inject",
    "request_factory",
    "websocket_factory",
    "wireup_asgi_middleware",
]


def _update_lifespan(app: Starlette) -> None:
    old_lifespan = app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[Any]:
        async with old_lifespan(app) as state:
            yield state

        await get_app_container(app).close()

    app.router.lifespan_context = lifespan


def setup(container: AsyncContainer, app: Starlette) -> None:
    """Integrate Wireup with a Starlette application.

    This sets up the application to use Wireup's dependency injection system and closes the container
    on application shutdown. Note, for this to work correctly, there should be no more middleware added after the call
    to this function.
    """

    _update_lifespan(app)
    app.state.wireup_container = container
    app.add_middleware(wireup_asgi_middleware)
