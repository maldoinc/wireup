from contextvars import ContextVar

from litestar import Litestar, Request
from litestar.connection.base import StateT

from wireup._decorators import inject_from_container_unchecked
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer

current_request: ContextVar[Request[None, None, StateT]] = ContextVar("wireup_fastapi_request")


def setup(container: AsyncContainer, app: Litestar) -> None:
    """Integrate Wireup with a Starlette application.

    This sets up the application to use Wireup's dependency injection system.
    It adds the WireupAsgiMiddleware to the application and associates the container with the app state.
    Note, for this to work correctly, there should be no more middleware added after the call to this function.
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


inject = inject_from_container_unchecked(get_request_container)
