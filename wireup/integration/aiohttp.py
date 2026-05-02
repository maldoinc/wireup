from collections.abc import Awaitable, Callable, Iterable
from contextvars import ContextVar
from typing import Protocol

from aiohttp import web

import wireup
from wireup._annotations import InjectableDeclaration, injectable
from wireup.errors import WireupError
from wireup.ioc.container.async_container import ScopedAsyncContainer

_request_container: ContextVar[ScopedAsyncContainer] = ContextVar("_wireup_container")
_container_key = "wireup_container"


class _WireupHandler(Protocol):
    router: web.RouteTableDef


def route(fn: Callable[..., Awaitable[web.StreamResponse]]) -> Callable[[web.Request], Awaitable[web.StreamResponse]]:
    return fn  # type: ignore[reportReturnType]


@injectable(lifetime="scoped")
def aiohttp_request_factory() -> web.Request:
    """Provide the current aiohttp request as a dependency.

    Note that this requires the Wireup-aiohttp integration to be set up.
    """
    msg = "aiohttp.web.Request in wireup is only available during a request."
    raise WireupError(msg)


def _inject_routes(container: wireup.AsyncContainer, app: web.Application, *, middleware_mode: bool) -> None:
    if middleware_mode:
        inject_scoped = wireup.inject_from_container(container, get_request_container)
    else:
        inject_scoped = wireup.inject_from_container(
            container,
            _context_creator={web.Request: "args[0]"},
        )

    for route in app.router.routes():
        route._handler = inject_scoped(route._handler)


async def _instantiate_class_based_handlers(
    container: wireup.AsyncContainer,
    app: web.Application,
    handlers: Iterable[type[_WireupHandler]],
) -> None:
    for handler_type in handlers:
        instance = await container.get(handler_type)

        for class_route in handler_type.router:
            for app_route in app.router.routes():
                if app_route._handler is class_route.handler:  # type: ignore[reportAttributeAccessIssue]
                    app_route._handler = getattr(instance, app_route._handler.__name__)


def _get_startup_event(
    container: wireup.AsyncContainer,
    handlers: Iterable[type[_WireupHandler]] | None,
    *,
    middleware_mode: bool,
) -> Callable[[web.Application], Awaitable[None]]:
    if handlers:
        for handler_type in handlers:
            container._registry.extend(impls=[InjectableDeclaration(handler_type)])

    async def _inner(app: web.Application) -> None:
        if handlers:
            await _instantiate_class_based_handlers(container, app, handlers)

        _inject_routes(container, app, middleware_mode=middleware_mode)

    return _inner


def setup(
    container: wireup.AsyncContainer,
    app: web.Application,
    handlers: Iterable[type[_WireupHandler]] | None = None,
    *,
    middleware_mode: bool = True,
) -> None:
    """Integrate Wireup with AIOHTTP.

    If you need access to `aiohttp.web.Request` in your injectables, add this module to the container's injectables.

    :param container: A Wireup async container.
    :param app: An AIOHTTP server application.
    :param handlers: A list of Wireup class-based handlers.
    See: https://maldoinc.github.io/wireup/latest/integrations/aiohttp/class_based_handlers/
    :param middleware_mode: If True, adds AIOHTTP middleware that exposes the scoped request container
        via `get_request_container`. Set to False to skip middleware and use context-seeded injection
        in route wrappers for better request-path performance.
    """

    async def _on_cleanup(_app: web.Application) -> None:
        await container.close()

    @web.middleware
    async def _wireup_middleware(
        request: web.Request,
        handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
    ) -> web.StreamResponse:
        async with container.enter_scope({web.Request: request}) as scoped_container:
            token = _request_container.set(scoped_container)
            request[_container_key] = scoped_container
            try:
                return await handler(request)
            finally:
                _request_container.reset(token)

    if handlers:
        for handler_type in handlers:
            app.router.add_routes(handler_type.router)

    if middleware_mode:
        app.middlewares.insert(0, _wireup_middleware)

    app.on_startup.append(_get_startup_event(container, handlers, middleware_mode=middleware_mode))
    app.on_cleanup.append(_on_cleanup)
    app[_container_key] = container


def get_app_container(app: web.Application) -> wireup.AsyncContainer:
    """Return the container associated with the given AIOHTTP application."""
    return app[_container_key]


def get_request_container() -> ScopedAsyncContainer:
    """When inside a request, returns the scoped container instance handling the current request.

    This requires setup(..., middleware_mode=True).
    """
    return _request_container.get()
