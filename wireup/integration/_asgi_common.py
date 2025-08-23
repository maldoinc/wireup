import inspect
from contextvars import ContextVar
from typing import Any, Callable, Dict, Type, TypeVar

from wireup._annotations import service
from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer

T = TypeVar("T", bound=Any)

current_request: ContextVar[Any] = ContextVar("wireup_request")


def make_request_factory(request_type: Type[T]) -> Callable[[], T]:
    @service(lifetime="scoped")
    def request_factory() -> T:
        msg = f"{request_type.__name__} in Wireup is only available during a request."
        try:
            res = current_request.get()
            if not isinstance(res, request_type):
                raise WireupError(msg)

            return res
        except LookupError as e:
            raise WireupError(msg) from e

    # Ensure runtime introspection shows the correct return type
    request_factory.__annotations__ = dict(request_factory.__annotations__)
    request_factory.__annotations__["return"] = request_type

    request_factory.__signature__ = inspect.signature(request_factory).replace(return_annotation=request_type)  # type: ignore[reportFunctionMemberAccess]

    return request_factory


def make_asgi_middleware(request_type: type, websocket_type: type) -> Callable[[Any], Any]:
    def _wireup_middleware(app: Any) -> Any:
        async def _middleware(scope: Dict[str, Any], receive: Dict[str, Any], send: Dict[str, Any]) -> None:
            if scope["type"] not in ("http", "websocket"):
                return await app(scope, receive, send)

            if scope["type"] == "http":
                request = request_type(scope, receive, send)
            else:
                request = websocket_type(scope, receive, send)

            token = current_request.set(request)
            try:
                async with request.app.state.wireup_container.enter_scope() as scoped_container:
                    request.state.wireup_container = scoped_container
                    await app(scope, receive, send)
            finally:
                current_request.reset(token)

        return _middleware

    return _wireup_middleware


def get_app_container(app: Any) -> AsyncContainer:
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
"""Inject dependencies into functions. Decorate endpoints with this to use Wireup's
dependency injection and use `Injected[T]` or `Annotated[T, Inject()]` to specify dependencies.
The decorated function can be any function in the request path such as route handlers or middleware,
as long as the request is active Wireup is able to inject the dependencies.
"""
