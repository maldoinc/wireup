import contextlib
import functools
import inspect
from contextvars import ContextVar
from typing import Any, AsyncIterator, Awaitable, Callable, List, Optional, Type, TypeVar

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.routing import APIRoute, APIWebSocketRoute
from starlette.routing import BaseRoute

from wireup import DependencyContainer
from wireup.errors import WireupError
from wireup.integration.util import is_view_using_container
from wireup.ioc.types import ServiceLifetime

current_request: ContextVar[Request] = ContextVar("wireup_fastapi_request")
T = TypeVar("T")


def controller(router: APIRouter) -> Callable[[T], T]:
    """Mark this class as a Class-Based route provider for fastapi powered by Wireup Dependencies."""

    def decorator(cls: T) -> T:
        cls.__router__ = router  # type:ignore[reportAttributeAccessIssue]
        return cls

    return decorator


async def _wireup_request_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    token = current_request.set(request)
    try:
        return await call_next(request)
    finally:
        current_request.reset(token)


def _fastapi_request_factory() -> Request:
    try:
        return current_request.get()
    except LookupError as e:
        msg = "fastapi.Request in wireup is only available during a request."
        raise WireupError(msg) from e


def _autowire_views(container: DependencyContainer, routes: List[BaseRoute]) -> None:
    for route in routes:
        if (
            isinstance(route, (APIRoute, APIWebSocketRoute))
            and route.dependant.call
            and is_view_using_container(container, route.dependant.call)
        ):
            target = route.dependant.call
            route.dependant.call = container.autowire(target)
            # Remove Request as a dependency from this target.
            # Let fastapi inject it instead and avoid duplicated work.
            container._registry.context.remove_dependency_type(target, Request)  # type: ignore[reportPrivateUsage]  # noqa: SLF001


def _with_self(instance: Any, fn: Callable[..., Any]) -> Callable[..., Any]:
    res = functools.wraps(fn)(functools.partial(fn, self=instance))
    sig = inspect.signature(res)
    res.__signature__ = sig.replace(parameters=[p for p in sig.parameters.values() if p.name != "self"])  # type: ignore[reportAttributeAccessIssue]
    res.__annotations__ = {k: v for k, v in res.__annotations__.items() if k != "self"}

    return res


def _register_class_based_routes(app: FastAPI, container: DependencyContainer, cls: Type[Any]) -> None:
    container.register(cls)
    r: APIRouter = cls.__router__  # type: ignore[reportUnknownMemberType]
    instance = container.get(cls)

    for route in r.routes:
        if isinstance(route, (APIRoute, APIWebSocketRoute)):
            method_name = route.endpoint.__name__
            unbound_method = getattr(cls, method_name)

            if route.endpoint is unbound_method:
                route.endpoint = getattr(instance, method_name)
            else:
                route.endpoint = _with_self(instance, route.endpoint)

    app.include_router(r)
    _autowire_views(container, r.routes)


def setup(container: DependencyContainer, app: FastAPI, *, class_routes: Optional[List[type]] = None) -> None:
    """Integrate Wireup with FastAPI.

    This will automatically inject dependencies on FastAPI routers.
    """
    current_lifespan = app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def _lifespan_wrapper(app: FastAPI) -> AsyncIterator[Any]:
        for route in class_routes or []:
            _register_class_based_routes(app, container, route)

        async with current_lifespan(app) as cl:
            yield cl

    app.router.lifespan_context = _lifespan_wrapper
    container.register(_fastapi_request_factory, lifetime=ServiceLifetime.TRANSIENT)
    app.middleware("http")(_wireup_request_middleware)
    _autowire_views(container, app.routes)
    app.state.wireup_container = container


def get_container(app: FastAPI) -> DependencyContainer:
    """Return the container associated with the given application."""
    return app.state.wireup_container
