import contextlib
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

import fastapi
from fastapi import FastAPI
from fastapi.routing import APIRoute, APIWebSocketRoute
from starlette.routing import BaseRoute
from typing_extensions import Protocol

from wireup import inject_from_container
from wireup._annotations import ServiceDeclaration
from wireup.errors import WireupError
from wireup.integration.starlette import (
    WireupAsgiMiddleware,
    current_request,
    get_app_container,
    get_request_container,
    request_factory,
    websocket_factory,
)
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer
from wireup.ioc.container.sync_container import ScopedSyncContainer
from wireup.ioc.types import AnyCallable
from wireup.ioc.validation import (
    assert_dependencies_valid,
    get_inject_annotated_parameters,
    hide_annotated_names,
)

__all__ = [
    "WireupRoute",
    "get_app_container",
    "get_request_container",
    "request_factory",
    "setup",
    "websocket_factory",
]


class _ClassBasedHandlersProtocol(Protocol):
    router: fastapi.APIRouter


class WireupRoute(APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        hide_annotated_names(endpoint)
        super().__init__(path=path, endpoint=endpoint, **kwargs)


def _inject_fastapi_route(
    *,
    container: AsyncContainer,
    target: AnyCallable,
    http_connection_param_name: str,
    remove_http_connection_from_arguments: bool,
    add_custom_middleware: bool,
) -> AnyCallable:
    # Warn: Make sure the logic evolves with the _wireup_request_middleware function.
    @contextlib.contextmanager
    def _request_middleware(
        scoped_container: Union[ScopedAsyncContainer, ScopedSyncContainer],
        _args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> Iterator[None]:
        request = kwargs[http_connection_param_name]
        request.state.wireup_container = scoped_container
        token = current_request.set(request)
        try:
            if remove_http_connection_from_arguments:
                del kwargs[http_connection_param_name]
            yield
        finally:
            current_request.reset(token)

    return inject_from_container(container, middleware=_request_middleware if add_custom_middleware else None)(target)


def _inject_routes(container: AsyncContainer, routes: List[BaseRoute], *, is_using_asgi_middleware: bool) -> None:
    for route in routes:
        if not (
            isinstance(route, (APIRoute, APIWebSocketRoute))
            and route.dependant.call
            and get_inject_annotated_parameters(route.dependant.call)
        ):
            continue

        # When using the asgi middleware, the request context variable is set there.
        # and we can get the scoped container from the request.
        if isinstance(route, APIRoute) and is_using_asgi_middleware:
            route.dependant.call = inject_from_container(container, get_request_container)(route.dependant.call)
            continue

        # This is now either a websocket route
        # or an APIRoute but the asgi middleware is not used.
        # In this case we need to use the custom route middleware to extract the current request/websocket.
        add_custom_middleware = isinstance(route, APIWebSocketRoute) or not is_using_asgi_middleware
        is_http_connection_in_signature = route.dependant.http_connection_param_name is not None

        # Setting http_connection_param_name forces FastAPI to pass the current HTTPConnection
        # to the route handler regardless of whether it was in the signature.
        # It is then extracted in the inject_from_container middleware to set the relevant context variable.
        if not route.dependant.http_connection_param_name:
            route.dependant.http_connection_param_name = "_fastapi_http_connection"

        route.dependant.call = _inject_fastapi_route(
            container=container,
            target=route.dependant.call,
            http_connection_param_name=route.dependant.http_connection_param_name,
            # If the HTTPConnection was not in the signature, it needs to be removed from the arguments
            # when calling the route handler.
            remove_http_connection_from_arguments=not is_http_connection_in_signature,
            add_custom_middleware=add_custom_middleware,
        )


async def _instantiate_class_based_route(
    app: FastAPI,
    container: AsyncContainer,
    cls: Type[_ClassBasedHandlersProtocol],
) -> None:
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
                    "Class-Based Handlers require the endpoint be unmodified! "
                    "If you want to decorate specific methods you need to place a decorator before the @router one."
                )
                raise WireupError(msg)

    app.include_router(cls.router)
    # Now that the router is included revert the endpoints to the original ones
    # as fastapi will have made a copy of things.
    for route in cls.router.routes:
        if isinstance(route, (APIRoute, APIWebSocketRoute)):
            route.endpoint = getattr(cls, route.endpoint.__name__)


def _update_lifespan(
    app: FastAPI,
    class_based_routes: Optional[Iterable[Type[_ClassBasedHandlersProtocol]]] = None,
    *,
    is_using_asgi_middleware: bool,
) -> None:
    old_lifespan = app.router.lifespan_context
    container = get_app_container(app)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[Any]:
        if class_based_routes:
            for cbr in class_based_routes:
                container._registry._extend_with_services(abstracts=[], impls=[ServiceDeclaration(cbr)])
            assert_dependencies_valid(container)

            for cbr in class_based_routes:
                await _instantiate_class_based_route(app, container, cbr)

            _inject_routes(container, app.routes, is_using_asgi_middleware=is_using_asgi_middleware)

        async with old_lifespan(app) as state:
            yield state

        await container.close()

    app.router.lifespan_context = lifespan


def setup(
    container: AsyncContainer,
    app: FastAPI,
    *,
    class_based_handlers: Optional[Iterable[Type[_ClassBasedHandlersProtocol]]] = None,
    middleware_mode: bool = False,
) -> None:
    """Integrate Wireup with FastAPI.

    Setup performs the following:
    * Injects dependencies into HTTP and WebSocket routes.
    * Closes the Wireup container upon app shutdown using the lifespan context.

    :param container: An async container created via `wireup.create_async_container`.
    :param app: The FastAPI application to integrate with. All routes must have been added to the app before this call.
    :param class_based_handlers: A list of class-based handlers to register.
    These classes must have a `router` attribute of type `fastapi.APIRouter`.
    Warning: Do not include these with fastapi directly.
    :param middleware_mode: If True, the container is exposed in fastapi middleware.
    Note, for this to work correctly, there should be no more middleware added after the call to this function.

    For more details, visit: https://maldoinc.github.io/wireup/latest/integrations/fastapi/
    """
    app.state.wireup_container = container
    if middleware_mode:
        app.add_middleware(WireupAsgiMiddleware)
    _update_lifespan(
        app,
        class_based_routes=class_based_handlers,
        is_using_asgi_middleware=middleware_mode,
    )
    # With class-based handlers, injection happens in the lifespan context
    # and the routes are injected there since some of the dependencies of the class-based handlers may be async.
    # If no class-based handlers are used, we inject them immediately.
    if not class_based_handlers:
        _inject_routes(container, app.routes, is_using_asgi_middleware=middleware_mode)
