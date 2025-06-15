import contextlib
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Dict, Iterable, Iterator, Optional, Protocol, Tuple, Type, Union

from aiohttp import web

import wireup
from wireup._annotations import service
from wireup.errors import WireupError
from wireup.ioc.container.async_container import ScopedAsyncContainer
from wireup.ioc.container.sync_container import ScopedSyncContainer

current_request: ContextVar[web.Request] = ContextVar("wireup_aiohttp_request")
_container_key = "wireup_container"


class _WireupHandler(Protocol):
    router: web.RouteTableDef


def route(fn: Callable[..., Awaitable[web.StreamResponse]]) -> Callable[[web.Request], Awaitable[web.StreamResponse]]:
    return fn  # type: ignore[reportReturnType]


@contextlib.contextmanager
def _route_middleware(
    scoped_container: Union[ScopedAsyncContainer, ScopedSyncContainer],
    args: Tuple[Any],
    _kwargs: Dict[str, Any],
) -> Iterator[None]:
    request: web.Request = args[0]
    request[_container_key] = scoped_container

    token = current_request.set(request)
    try:
        yield
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
    inject_scoped = wireup.inject_from_container(container, middleware=_route_middleware)

    for route in app.router.routes():
        route._handler = inject_scoped(route._handler)


async def _instantiate_class_based_handlers(
    container: wireup.AsyncContainer,
    app: web.Application,
    handlers: Iterable[Type[_WireupHandler]],
) -> None:
    for handler_type in handlers:
        instance = await container.get(handler_type)

        for class_route in handler_type.router:
            for app_route in app.router.routes():
                if app_route._handler is class_route.handler:  # type: ignore[reportAttributeAccessIssue]
                    app_route._handler = getattr(instance, app_route._handler.__name__)


def _get_startup_event(
    container: wireup.AsyncContainer, handlers: Optional[Iterable[Type[_WireupHandler]]]
) -> Callable[[web.Application], Awaitable[None]]:
    for handler_type in handlers or []:
        container._registry.register(handler_type)

    async def _inner(app: web.Application) -> None:
        if handlers:
            await _instantiate_class_based_handlers(container, app, handlers)

        _inject_routes(container, app)

    return _inner


def setup(
    container: wireup.AsyncContainer, app: web.Application, handlers: Optional[Iterable[Type[_WireupHandler]]] = None
) -> None:
    """Integrate Wireup with AIOHTTP.

    If you need access to `aiohttp.web.Request` in your services, add this module to the `service_modules` in your
    container's service modules.

    :param container: A Wireup async container.
    :param app: An AIOHTTP server application.
    :param handlers: A list of Wireup class-based handlers.
    See: https://maldoinc.github.io/wireup/latest/integrations/aiohttp/class_based_handlers/
    """

    async def _on_cleanup(_app: web.Application) -> None:
        await container.close()

    if handlers:
        for handler_type in handlers:
            app.router.add_routes(handler_type.router)

    app.on_startup.append(_get_startup_event(container, handlers))
    app.on_cleanup.append(_on_cleanup)
    app[_container_key] = container


def get_app_container(app: web.Application) -> wireup.AsyncContainer:
    """Return the container associated with the given AIOHTTP application."""
    return app[_container_key]


def get_request_container() -> ScopedAsyncContainer:
    """When inside a request, returns the scoped container instance handling the current request."""
    return current_request.get()[_container_key]
