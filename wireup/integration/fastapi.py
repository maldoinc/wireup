from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, Iterable

import fastapi
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute, APIWebSocketRoute
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
from wireup.ioc.util import (
    get_inject_annotated_parameters,
    hide_annotated_names,
    injection_requires_scope,
    is_wireup_injected,
)
from wireup.renderer._consumers import ConsumerMetadata
from wireup.renderer._dependencies import DependencyReference, ServiceDependencyReference
from wireup.renderer.full_page import GraphEndpointOptions, render_graph_page

if TYPE_CHECKING:
    from starlette.routing import BaseRoute

    from wireup.ioc.container.async_container import AsyncContainer
    from wireup.ioc.types import AnyCallable

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


def _inject_route_with_connection_context(  # noqa: PLR0913
    *,
    container: AsyncContainer,
    target: AnyCallable,
    consumer_metadata: ConsumerMetadata,
    http_connection_param_name: str | None,
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
        consumer_metadata=consumer_metadata,
    )(target)


def _ensure_http_connection_param(route: APIRoute | APIWebSocketRoute) -> tuple[str, bool]:
    """Ensure FastAPI will pass the active connection and return param name + remove flag."""
    has_connection_param_in_signature = route.dependant.http_connection_param_name is not None
    if not route.dependant.http_connection_param_name:
        route.dependant.http_connection_param_name = "_fastapi_http_connection"

    return route.dependant.http_connection_param_name, not has_connection_param_in_signature


def _get_consumer_metadata(route: APIRoute | APIWebSocketRoute) -> ConsumerMetadata:
    methods = () if isinstance(route, APIWebSocketRoute) else tuple(sorted(route.methods or []))
    method_label = "WS" if isinstance(route, APIWebSocketRoute) else "|".join(methods) if methods else "ROUTE"
    consumer_id = f"{method_label} {route.path}"
    extra_dependencies: tuple[DependencyReference, ...] = ()

    bound_instance = getattr(route.dependant.call, "__self__", None)
    if bound_instance is not None:
        extra_dependencies = (
            ServiceDependencyReference(
                param_name="handler",
                service_id=f"{bound_instance.__class__.__module__}.{bound_instance.__class__.__qualname__}",
                qualifier=None,
            ),
        )

    return ConsumerMetadata(
        consumer_id=consumer_id,
        kind="fastapi_websocket" if isinstance(route, APIWebSocketRoute) else "fastapi_route",
        label=f"🌐 {consumer_id}",
        group="FastAPI",
        module=route.dependant.call.__module__,
        extra_dependencies=extra_dependencies,
    )


def _inject_routes(
    container: AsyncContainer,
    routes: list[BaseRoute],
    *,
    is_using_asgi_middleware: bool,
) -> None:
    for route in routes:
        if not (isinstance(route, (APIRoute, APIWebSocketRoute)) and route.dependant.call):
            continue

        # Injection wrappers compiled by Wireup set this marker.
        # If present, the route has already been wrapped and should not be wrapped again.
        if is_wireup_injected(route.dependant.call):
            continue

        names_to_inject = get_inject_annotated_parameters(route.dependant.call)
        if not names_to_inject:
            continue

        consumer_metadata = _get_consumer_metadata(route)

        # When using the asgi middleware, the request context variable is set there.
        # and we can get the scoped container from the request.
        if isinstance(route, APIRoute) and is_using_asgi_middleware:
            route.dependant.call = inject_from_container(
                container,
                get_request_container,
                consumer_metadata=consumer_metadata,
            )(route.dependant.call)
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
            consumer_metadata=consumer_metadata,
            http_connection_param_name=http_connection_param_name,
            remove_http_connection_from_arguments=remove_http_connection_from_arguments,
            is_websocket_route=isinstance(route, APIWebSocketRoute),
        )


def _setup_graph_routes(app: FastAPI, *, options: GraphEndpointOptions) -> None:
    async def _wireup_graph_page(request: Request) -> HTMLResponse:
        return HTMLResponse(
            render_graph_page(
                get_app_container(request.app),
                title=f"{app.title} - Wireup Graph",
                options=options,
            )
        )

    app.add_api_route("/_wireup", _wireup_graph_page, methods=["GET"], response_class=HTMLResponse)


async def _instantiate_class_based_route(
    app: FastAPI,
    container: AsyncContainer,
    cls: type[_ClassBasedHandlersProtocol],
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
    class_based_routes: Iterable[type[_ClassBasedHandlersProtocol]] | None = None,
    *,
    is_using_asgi_middleware: bool,
) -> None:
    old_lifespan = app.router.lifespan_context
    container = get_app_container(app)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[Any]:
        if class_based_routes and not getattr(app.state, "wireup_cbr_initialized", False):
            for cbr in class_based_routes:
                if not container._registry.is_type_with_qualifier_known(cbr, None):
                    container._registry.extend(impls=[InjectableDeclaration(cbr)])

            for cbr in class_based_routes:
                await _instantiate_class_based_route(app, container, cbr)

            app.state.wireup_cbr_initialized = True

        # Inject routes on every lifespan start. This is idempotent and skips callables already wrapped by Wireup.
        _inject_routes(container, app.routes, is_using_asgi_middleware=is_using_asgi_middleware)

        async with old_lifespan(app) as state:
            yield state

        await container.close()

    app.router.lifespan_context = lifespan


def setup(  # noqa: PLR0913
    container: AsyncContainer,
    app: FastAPI,
    *,
    class_based_handlers: Iterable[type[_ClassBasedHandlersProtocol]] | None = None,
    middleware_mode: bool = False,
    add_graph_endpoint: bool = False,
    graph_endpoint_options: GraphEndpointOptions | None = None,
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
    :param add_graph_endpoint: If True, mount the `/_wireup` endpoint exposing
        the Wireup graph viewer and raw graph JSON.
    :param graph_endpoint_options: Optional graph endpoint configuration.

    For more details, visit: https://maldoinc.github.io/wireup/latest/integrations/fastapi/
    """
    app.state.wireup_container = container
    _expose_wireup_task(container)
    if add_graph_endpoint:
        _setup_graph_routes(app, options=graph_endpoint_options or GraphEndpointOptions())
    if middleware_mode:
        app.add_middleware(WireupAsgiMiddleware, include_websocket=False)
    _update_lifespan(
        app,
        class_based_routes=class_based_handlers,
        is_using_asgi_middleware=middleware_mode,
    )
    # Lifespan always runs an injection pass (including routes added after setup).
    # For non-class-based setups we also inject immediately so existing routes are ready without waiting for startup.
    if not class_based_handlers:
        _inject_routes(
            container,
            app.routes,
            is_using_asgi_middleware=middleware_mode,
        )


inject = inject_from_container_unchecked(get_request_container, hide_annotated_names=True)
"""Inject dependencies into request-time FastAPI helpers.

Use this for non-route functions that still run during a request lifecycle, such as
custom decorators, dependency helper functions, and middleware helpers.
"""
