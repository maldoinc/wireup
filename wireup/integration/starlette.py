from contextvars import ContextVar
from typing import Union

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket

from wireup._annotations import service
from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer

current_request: ContextVar[Union[Request, WebSocket]] = ContextVar("wireup_fastapi_request")


@service(lifetime="scoped")
def request_factory() -> Request:
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
def websocket_factory() -> WebSocket:
    """Provide the current WebSocket as a dependency."""
    msg = "WebSocket in Wireup is only available in a websocket connection."
    try:
        res = current_request.get()
        if not isinstance(res, WebSocket):
            raise WireupError(msg)

        return res
    except LookupError as e:
        raise WireupError(msg) from e


class WireupAsgiMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)

        if scope["type"] == "http":
            request = Request(scope, receive=receive, send=send)
        else:
            request = WebSocket(scope, receive, send)

        token = current_request.set(request)
        try:
            async with request.app.state.wireup_container.enter_scope() as scoped_container:
                request.state.wireup_container = scoped_container
                await self.app(scope, receive, send)
        finally:
            current_request.reset(token)


def setup(container: AsyncContainer, app: Starlette) -> None:
    """Integrate Wireup with a Starlette application.

    This sets up the application to use Wireup's dependency injection system.
    It adds the WireupAsgiMiddleware to the application and associates the container with the app state.
    Note, for this to work correctly, there should be no more middleware added after the call to this function.
    """

    app.state.wireup_container = container
    app.add_middleware(WireupAsgiMiddleware)


def get_app_container(app: Starlette) -> AsyncContainer:
    """Return the container associated with the given application.

    This is the instance created via `wireup.create_async_container`.
    Use this when you need the container outside of the request context lifecycle.
    """
    return app.state.wireup_container


def get_request_container() -> ScopedAsyncContainer:
    """When inside a request, returns the scoped container instance handling the current request.

    This is what you almost always want.It has all the information the app container has in addition
    to data specific to the current request.
    """
    return current_request.get().state.wireup_container


inject = inject_from_container_unchecked(get_request_container)
"""Inject dependencies into Starlette endpoints. Decorate your endpoint functions with this to use Wireup's
dependency injection and use `Injected[T]` or `Annotated[T, Inject()]` to specify dependencies.
"""
