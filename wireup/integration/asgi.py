from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

    from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer

__all__ = ["WireupASGIMiddleware", "get_request_container", "inject"]

_current_container: ContextVar[ScopedAsyncContainer] = ContextVar("wireup_asgi_container")


class WireupASGIMiddleware:
    """ASGI middleware that manages a Wireup scope for each HTTP/WebSocket request."""

    def __init__(self, app: ASGIApp, container: AsyncContainer) -> None:
        self.app = app
        self.container = container

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)

        async with self.container.enter_scope() as scoped_container:
            token = _current_container.set(scoped_container)
            try:
                await self.app(scope, receive, send)
            finally:
                _current_container.reset(token)


def get_request_container() -> ScopedAsyncContainer:
    """Return the Wireup container for the current HTTP/WebSocket request."""
    msg = "Wireup request container is only available during an active HTTP/WebSocket request."
    try:
        return _current_container.get()
    except LookupError as e:
        raise WireupError(msg) from e


inject = inject_from_container_unchecked(get_request_container, hide_annotated_names=True)
"""Inject dependencies using the current ASGI request scope."""
