from contextvars import ContextVar
from typing import Any

from litestar import Litestar, Request
from litestar.types import ASGIApp, Receive, Scope, Send

from wireup._annotations import service
from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer

current_request: ContextVar[Request[Any, Any, Any]] = ContextVar("wireup_fastapi_request")


@service(lifetime="scoped")
def request_factory() -> Request[Any, Any, Any]:
    """Provide the current request as a dependency."""
    try:
        return current_request.get()
    except LookupError as e:
        msg = "Request in Wireup is only available during a request."
        raise WireupError(msg) from e


def wireup_middleware(app: ASGIApp) -> ASGIApp:
    async def _middleware(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await app(scope, receive, send)

        request: Request[Any, Any, Any] = Request(scope, receive, send)
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
    """
    app.state.wireup_container = container


def get_app_container(app: Litestar) -> AsyncContainer:
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


inject = inject_from_container_unchecked(get_request_container, hide_wireup_params=True)
