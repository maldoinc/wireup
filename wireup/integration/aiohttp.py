from contextvars import ContextVar
from typing import Awaitable, Callable, Iterable, Optional, Protocol, Type

from aiohttp import web

import wireup
from wireup._annotations import service
from wireup.errors import WireupError
from wireup.integration.util import is_callable_using_wireup_dependencies

current_request: ContextVar[web.Request] = ContextVar("wireup_aiohttp_request")


class _WireupHandler(Protocol):
    router: web.RouteTableDef


def route(
    fn: Callable[..., Awaitable[web.StreamResponse]],
) -> Callable[[web.Request], Awaitable[web.StreamResponse]]:
    return fn  # type: ignore[reportReturnType]


@web.middleware
async def _wireup_middleware(
    request: web.Request, handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
) -> web.StreamResponse:
    token = current_request.set(request)
    try:
        return await handler(request)
    finally:
        current_request.reset(token)


@service(lifetime="scoped")
def aiohttp_request_factory() -> web.Request:
    """Provide the current aiohttp request as a dependency.

    Note that this requires the Wireup-aiohttp integration to be set up.
    """
    try:
        return current_request.get()
    except LookupError as e:
        msg = "aiohttp.web.Request in wireup is only available during a request."
        raise WireupError(msg) from e


def _inject_routes(container: wireup.AsyncContainer, app: web.Application) -> None:
    inject_scoped = wireup.inject_from_container(container)

    for route in app.router.routes():
        if is_callable_using_wireup_dependencies(route._handler):
            route._handler = inject_scoped(route._handler)


async def _setup_handlers(
    container: wireup.AsyncContainer, app: web.Application, handlers: Iterable[Type[_WireupHandler]]
) -> None:
    for handler_type in handlers:
        instance = await container.get(handler_type)

        if not (hasattr(handler_type, "router") and isinstance(handler_type.router, web.RouteTableDef)):  # type: ignore[reportUnnecessaryIsInstance]
            msg = (
                f"Handler {handler_type} does not have an attribute named 'router'. "
                "Your handlers must be classes that have an attribute named 'router'."
            )
            raise WireupError(msg)

        for class_route in handler_type.router:
            for app_route in app.router.routes():
                if app_route._handler is class_route.handler:  # type: ignore[reportAttributeAccessIssue]
                    app_route._handler = getattr(instance, app_route._handler.__name__)


def _get_startup_event(
    container: wireup.AsyncContainer, handlers: Optional[Iterable[Type[_WireupHandler]]]
) -> Callable[[web.Application], Awaitable[None]]:
    if handlers:
        for handler_type in handlers:
            container._registry.register(handler_type)

    async def _inner(app: web.Application) -> None:
        if handlers:
            await _setup_handlers(container, app, handlers)

        _inject_routes(container, app)

    return _inner


def setup(
    container: wireup.AsyncContainer, app: web.Application, handlers: Optional[Iterable[Type[_WireupHandler]]] = None
) -> None:
    """Integrate Wireup with AIOHTTP.

    Setup performs the following:
    * Injects dependencies into AIOHTTP routes.
    * Adds a Wireup Middleware, allowing you to request the container in middlewares.

    If you need access to `aiohttp.web.Request` in your services, add this module to the `service_modules` in your
    container or add `aiohttp_request_factory` to the `services` parameter.
    """

    app.middlewares.append(_wireup_middleware)

    async def _on_cleanup(_app: web.Application) -> None:
        await container.close()

    app.on_startup.append(_get_startup_event(container, handlers))
    app.on_cleanup.append(_on_cleanup)
