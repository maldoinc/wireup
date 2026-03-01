import contextlib
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

import fastapi
from fastapi import FastAPI, Request, WebSocket
from fastapi.routing import APIRoute, APIWebSocketRoute
from starlette.routing import BaseRoute
from typing_extensions import Protocol

from wireup import inject_from_container
from wireup._annotations import InjectableDeclaration
from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.integration.starlette import (
    WireupAsgiMiddleware,
    WireupTask,
    _expose_wireup_task,
    get_app_container,
    get_request_container,
    request_factory,
    websocket_factory,
)
from wireup.ioc.container.async_container import AsyncContainer
from wireup.ioc.types import AnyCallable
from wireup.ioc.util import (
    get_inject_annotated_parameters,
    hide_annotated_names,
    injection_requires_scope,
)

__all__ = [
    "WireupRoute",
    "WireupTask",
    "get_app_container",
    "get_request_container",
    "inject",
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


def _inject_route_with_connection_context(
    *,
    container: AsyncContainer,
    target: AnyCallable,
    http_connection_param_name: Optional[str],
    remove_http_connection_from_arguments: bool,
    is_websocket_route: bool,
) -> AnyCallable:
    return inject_from_container(
        container,
        _context_creator={
            (WebSocket if is_websocket_route else Request): f"kwargs.pop('{http_connection_param_name}')"
            if remove_http_connection_from_arguments
            else f"kwargs['{http_connection_param_name}']"
        }
        if http_connection_param_name
        else None,
    )(target)


def _ensure_http_connection_param(route: Union[APIRoute, APIWebSocketRoute]) -> Tuple[str, bool]:
    """Ensure FastAPI will pass the active connection and return param name + remove flag."""
    has_connection_param_in_signature = route.dependant.http_connection_param_name is not None
    if not route.dependant.http_connection_param_name:
        route.dependant.http_connection_param_name = "_fastapi_http_connection"

    return route.dependant.http_connection_param_name, not has_connection_param_in_signature


def _inject_routes(
    container: AsyncContainer,
    routes: List[BaseRoute],
    *,
    is_using_asgi_middleware: bool,
    skip_calls: Optional[List[AnyCallable]] = None,
) -> List[AnyCallable]:
    injected_calls: List[AnyCallable] = []
    # setup() can inject once and lifespan injects again at startup.
    # Track already-injected route callables so routes are wrapped at most once.
    skip_calls_set = set(skip_calls or [])

    for route in routes:
        if not (isinstance(route, (APIRoute, APIWebSocketRoute)) and route.dependant.call):
            continue

        if route.dependant.call in skip_calls_set:
            continue

        names_to_inject = get_inject_annotated_parameters(route.dependant.call)
        if not names_to_inject:
            continue

        # When using the asgi middleware, the request context variable is set there.
        # and we can get the scoped container from the request.
        if isinstance(route, APIRoute) and is_using_asgi_middleware:
            route.dependant.call = inject_from_container(container, get_request_container)(route.dependant.call)
            injected_calls.append(route.dependant.call)
            continue

        # We now are either in a websocket endpoint or HTTP without middleware_mode.
        # If the endpoint requires a scope, extract request/websocket from it, otherwise just leave it be
        # and inject whatever singletons.
        if injection_requires_scope(names_to_inject, container):
            http_connection_param_name, remove_http_connection_from_arguments = _ensure_http_connection_param(route)
        else:
            http_connection_param_name, remove_http_connection_from_arguments = None, False

        route.dependant.call = _inject_route_with_connection_context(
            container=container,
            target=route.dependant.call,
            http_connection_param_name=http_connection_param_name,
            remove_http_connection_from_arguments=remove_http_connection_from_arguments,
            is_websocket_route=isinstance(route, APIWebSocketRoute),
        )
        injected_calls.append(route.dependant.call)

    return injected_calls


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
    injected_route_calls: Optional[List[AnyCallable]] = None,
    *,
    is_using_asgi_middleware: bool,
) -> None:
    old_lifespan = app.router.lifespan_context
    container = get_app_container(app)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[Any]:
        if class_based_routes:
            for cbr in class_based_routes:
                container._registry.extend(impls=[InjectableDeclaration(cbr)])

            for cbr in class_based_routes:
                await _instantiate_class_based_route(app, container, cbr)

            new_calls = _inject_routes(
                container,
                app.routes,
                is_using_asgi_middleware=is_using_asgi_middleware,
                skip_calls=injected_route_calls,
            )
            if injected_route_calls is not None:
                injected_route_calls.extend(new_calls)

        # Inject any new routes added after setup() but before app startup.
        new_calls = _inject_routes(
            container,
            app.routes,
            is_using_asgi_middleware=is_using_asgi_middleware,
            skip_calls=injected_route_calls,
        )
        if injected_route_calls is not None:
            injected_route_calls.extend(new_calls)

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
    :param app: The FastAPI application to integrate with. Best practice is to call setup after routes are added.
    If setup is called earlier, ensure FastAPI lifespan runs before handling requests (for example, use TestClient as a
    context manager in tests).
    :param class_based_handlers: A list of class-based handlers to register.
    These classes must have a `router` attribute of type `fastapi.APIRouter`.
    Warning: Do not include these with fastapi directly.
    :param middleware_mode: If True, the container is exposed in fastapi middleware.
    Note, for this to work correctly, there should be no more middleware added after the call to this function.

    For more details, visit: https://maldoinc.github.io/wireup/latest/integrations/fastapi/
    """
    app.state.wireup_container = container
    _expose_wireup_task(container)
    injected_route_calls: List[AnyCallable] = []
    if middleware_mode:
        app.add_middleware(WireupAsgiMiddleware, include_websocket=False)
    _update_lifespan(
        app,
        class_based_routes=class_based_handlers,
        injected_route_calls=injected_route_calls,
        is_using_asgi_middleware=middleware_mode,
    )
    # Lifespan always runs an injection pass (including routes added after setup).
    # For non-class-based setups we also inject immediately so existing routes are ready without waiting for startup.
    if not class_based_handlers:
        injected_route_calls.extend(
            _inject_routes(
                container,
                app.routes,
                is_using_asgi_middleware=middleware_mode,
                skip_calls=injected_route_calls,
            )
        )


inject = inject_from_container_unchecked(get_request_container, hide_annotated_names=True)
"""Inject dependencies into request-time FastAPI helpers.

Use this for non-route functions that still run during a request lifecycle, such as
custom decorators, dependency helper functions, and middleware helpers.
"""
