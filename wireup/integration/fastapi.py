from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Optional, Type, TypeVar

from fastapi import Depends, FastAPI, Request, Response
from fastapi.routing import APIRoute, APIWebSocketRoute

from wireup import DependencyContainer
from wireup.errors import WireupError
from wireup.integration.util import is_view_using_container
from wireup.ioc.types import Qualifier, ServiceLifetime, TemplatedString

current_request: ContextVar[Request] = ContextVar("wireup_fastapi_request")

T = TypeVar("T")


def WireupContainer() -> Callable[[], DependencyContainer]:
    def _depends(request: Request) -> DependencyContainer:
        return get_container(request.app)

    return Depends(_depends)


def WireupService(service: Type[T], qualifier: Optional[Qualifier] = None) -> Callable[..., T]:
    def _depends(request: Request) -> T:
        return get_container(request.app).get(service, qualifier)

    return Depends(_depends)


def WireupParameter(param: str) -> Callable[..., Any]:
    def _depends(request: Request) -> Any:
        return get_container(request.app).params.get(param)

    return Depends(_depends)


def WireupExpr(expr: str) -> Callable[..., Any]:
    def _depends(request: Request) -> Any:
        return get_container(request.app).params.get(TemplatedString(expr))

    return Depends(_depends)


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


def _autowire_views(container: DependencyContainer, app: FastAPI) -> None:
    for route in app.routes:
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


def setup(container: DependencyContainer, app: FastAPI) -> None:
    """Integrate Wireup with FastAPI.

    This will automatically inject dependencies on FastAPI routers.
    """
    container.register(_fastapi_request_factory, lifetime=ServiceLifetime.TRANSIENT)
    app.middleware("http")(_wireup_request_middleware)
    _autowire_views(container, app)
    app.state.wireup_container = container


def get_container(app: FastAPI) -> DependencyContainer:
    """Return the container associated with the given application."""
    return app.state.wireup_container
