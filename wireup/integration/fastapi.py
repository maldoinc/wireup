import contextlib
import functools
from contextvars import ContextVar
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
)

import fastapi
from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute, APIWebSocketRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import BaseRoute
from typing_extensions import Protocol

from wireup import inject_from_container, service
from wireup.errors import WireupError
from wireup.integration.util import is_callable_using_wireup_dependencies
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer
from wireup.ioc.types import ParameterWrapper
from wireup.ioc.validation import get_valid_injection_annotated_parameters, hide_annotated_names

current_request: ContextVar[Request] = ContextVar("wireup_fastapi_request")
current_ws_container: ContextVar[ScopedAsyncContainer] = ContextVar("wireup_fastapi_container")

T = TypeVar("T", bound=type)


class _ClassBasedRouteProtocol(Protocol):
    router: fastapi.APIRouter


class WireupRoute(APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        hide_annotated_names(endpoint)
        super().__init__(path=path, endpoint=endpoint, **kwargs)


async def _wireup_request_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    token = current_request.set(request)
    try:
        async with request.app.state.wireup_container.enter_scope() as scoped_container:
            request.state.wireup_container = scoped_container
            return await call_next(request)
    finally:
        current_request.reset(token)


@service(lifetime="scoped")
def fastapi_request_factory() -> Request:
    """Provide the current FastAPI request as a dependency.

    Note that this requires the Wireup-FastAPI integration to be set up.
    """
    try:
        return current_request.get()
    except LookupError as e:
        msg = (
            "The 'fastapi.Request' service in Wireup requires 'enable_middleware=True' during FastAPI integration. "
            "This service is also only accessible within the context of a request."
        )
        raise WireupError(msg) from e


# We need to inject websocket routes separately as the regular fastapi middlewares work only for http.
def _inject_websocket_route(container: AsyncContainer, target: Callable[..., Any]) -> Callable[..., Any]:
    names_to_inject = get_valid_injection_annotated_parameters(container, target)

    @functools.wraps(target)
    async def _inner(*args: Any, **kwargs: Any) -> Any:
        async with container.enter_scope() as scoped_container:
            token = current_ws_container.set(scoped_container)
            injected_names = {
                name: container.params.get(param.annotation.param)
                if isinstance(param.annotation, ParameterWrapper)
                else await scoped_container.get(param.klass, qualifier=param.qualifier_value)
                for name, param in names_to_inject.items()
                if param.annotation
            }

            try:
                return await target(*args, **{**kwargs, **injected_names})
            finally:
                current_ws_container.reset(token)

    return _inner


def _inject_routes(container: AsyncContainer, routes: List[BaseRoute], *, has_request_middleware: bool) -> None:
    inject_scoped = inject_from_container(container, get_request_container if has_request_middleware else None)

    for route in routes:
        if (
            isinstance(route, (APIRoute, APIWebSocketRoute))
            and route.dependant.call
            and is_callable_using_wireup_dependencies(route.dependant.call)
        ):
            target = route.dependant.call
            route.dependant.call = (
                inject_scoped(target) if isinstance(route, APIRoute) else _inject_websocket_route(container, target)
            )


async def _register_class_based_route(
    app: FastAPI, container: AsyncContainer, cls: Type[_ClassBasedRouteProtocol], *, has_request_middleware: bool
) -> None:
    container._registry.register(cls)
    instance = await container.get(cls)

    for route in cls.router.routes:
        if isinstance(route, (APIRoute, APIWebSocketRoute)):
            route_handler_name = route.endpoint.__name__
            unbound_method = getattr(cls, route_handler_name)

            if route.endpoint is unbound_method:
                route.endpoint = getattr(instance, route_handler_name)
            else:
                msg = (
                    f"Method {route_handler_name} of {cls} has been modified, possibly by the router's APIRoute."
                    "Class-Based Routes require the endpoint be unmodified! "
                    "If you want to decorate specific methods you need to place a decorator before the @router one."
                )
                raise WireupError(msg)

    _inject_routes(container, cls.router.routes, has_request_middleware=has_request_middleware)
    app.include_router(cls.router)

    # Now that the router is included revert the endpoints to the original ones
    # as fastapi will have made a copy of things.
    for route in cls.router.routes:
        if isinstance(route, (APIRoute, APIWebSocketRoute)):
            route.endpoint = getattr(cls, route.endpoint.__name__)


def _update_lifespan(
    container: AsyncContainer,
    app: FastAPI,
    class_based_routes: Optional[Iterable[Type[_ClassBasedRouteProtocol]]] = None,
    *,
    has_request_middleware: bool,
) -> None:
    old_lifespan = app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[Any]:
        if class_based_routes:
            for cbr in class_based_routes:
                await _register_class_based_route(app, container, cbr, has_request_middleware=has_request_middleware)

        async with old_lifespan(app) as state:
            yield state

        await container.close()

    app.router.lifespan_context = lifespan


def setup(
    container: AsyncContainer,
    app: FastAPI,
    *,
    class_based_routes: Optional[Iterable[Type[_ClassBasedRouteProtocol]]] = None,
    enable_middleware: bool = True,
) -> None:
    """Integrate Wireup with FastAPI.

    Setup performs the following:
    * Injects dependencies into HTTP and WebSocket routes.
    * Creates a new container scope for each request, with a scoped lifetime matching the request duration.
    * Closes the Wireup container upon app shutdown using the lifespan context.

    For more details, visit: https://maldoinc.github.io/wireup/latest/integrations/fastapi/

    Note: To trigger lifespan events in the FastAPI test client, use the client as a context manager.
    ```python
    @pytest.fixture()
    def client(app: FastAPI) -> Iterator[TestClient]:
        with TestClient(app) as client:
            yield client
    ```
    """
    middleware_enabled = enable_middleware
    if middleware_enabled:
        app.add_middleware(BaseHTTPMiddleware, dispatch=_wireup_request_middleware)

    _update_lifespan(container, app, class_based_routes, has_request_middleware=middleware_enabled)
    _inject_routes(container, app.routes, has_request_middleware=middleware_enabled)
    app.state.wireup_container = container


def get_app_container(app: FastAPI) -> AsyncContainer:
    """Return the container associated with the given FastAPI application."""
    return app.state.wireup_container


def get_request_container() -> ScopedAsyncContainer:
    """When inside a request, returns the scoped container instance handling the current request."""
    try:
        return current_request.get().state.wireup_container
    except LookupError:
        return current_ws_container.get()
