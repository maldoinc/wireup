import contextlib
from contextvars import ContextVar
from typing import Any, AsyncIterator

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket

from wireup._annotations import InjectableDeclaration, injectable
from wireup._decorators import inject_from_container, inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer
from wireup.ioc.types import AnyCallable

from functools import lru_cache

request_container: ContextVar[ScopedAsyncContainer] = ContextVar("wireup_scoped_container")


@injectable(lifetime="scoped")
def request_factory() -> Request:
    """Provide the current request as a dependency."""
    msg = "Request in Wireup is only available during a request."
    raise WireupError(msg)


@injectable(lifetime="scoped")
def websocket_factory() -> WebSocket:
    """Provide the current WebSocket as a dependency."""
    msg = "WebSocket in Wireup is only available in a websocket connection."
    raise WireupError(msg)


class WireupAsgiMiddleware:
    def __init__(self, app: ASGIApp, *, include_websocket: bool = True) -> None:
        self.app = app
        self.include_websocket = include_websocket

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        accepted_scope_types = {"http", "websocket"} if self.include_websocket else {"http"}
        if scope["type"] not in accepted_scope_types:
            return await self.app(scope, receive, send)

        if scope["type"] == "http":
            request = Request(scope, receive=receive, send=send)
        else:
            request = WebSocket(scope, receive, send)

        async with request.app.state.wireup_container.enter_scope({type(request): request}) as scoped_container:
            token = request_container.set(scoped_container)
            try:
                await self.app(scope, receive, send)
            finally:
                request_container.reset(token)


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
    app.add_middleware(WireupAsgiMiddleware)
    _expose_wireup_task(container)


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
    try:
        return request_container.get()
    except (LookupError, AttributeError) as e:
        msg = (
            "Wireup request container is unavailable in the current execution context.\n"
            "Common causes:\n"
            "1) The code is running outside an active HTTP/WebSocket request lifecycle.\n"
            "2) The call ran before Wireup middleware created the scoped container "
            "(middleware ordering issue). Ensure Wireup middleware runs outermost.\n"
            "3) FastAPI requires `setup(..., middleware_mode=True)` for `get_request_container()`.\n"
            "4) In FastAPI, middleware-backed request containers are HTTP-only; WebSocket handlers do not have one.\n"
            "Prefer `Injected[...]` for handler/service dependencies. Use `get_app_container(app)` outside request "
            "scope."
        )
        raise WireupError(msg) from e


class WireupTask:
    __slots__ = ("container", "_get_injected_wrapper",)

    def __init__(self, container: AsyncContainer) -> None:
        self.container = container
        self._get_injected_wrapper = lru_cache(maxsize=128)(inject_from_container(self.container))

    def __call__(self, fn: AnyCallable) -> Any:
        return self._get_injected_wrapper(fn)


inject = inject_from_container_unchecked(get_request_container, hide_annotated_names=True)
"""Inject dependencies into Starlette endpoints. Decorate your endpoint functions with this to use Wireup's
dependency injection and use `Injected[T]` or `Annotated[T, Inject()]` to specify dependencies.
"""


def _expose_wireup_task(container: AsyncContainer) -> None:
    if container._registry.is_type_with_qualifier_known(WireupTask, None):
        return

    def wireup_task_factory() -> WireupTask:
        return WireupTask(container)

    container._registry.extend(impls=[InjectableDeclaration(wireup_task_factory, as_type=WireupTask)])
