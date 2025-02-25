from __future__ import annotations

import asyncio
import functools
import importlib
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable

import django
import django.urls
from django.apps import AppConfig, apps
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern, URLResolver
from django.utils.decorators import sync_and_async_middleware

import wireup
from wireup import (
    ServiceLifetime,
)
from wireup.decorators import make_inject_decorator
from wireup.errors import WireupError
from wireup.ioc.container.scoped_container import async_container_force_sync_scope

if TYPE_CHECKING:
    from types import ModuleType

    from wireup.integration.django import WireupSettings
    from wireup.ioc.container.async_container import AsyncContainer
    from wireup.ioc.container.scoped_container import ScopedAsyncContainer, ScopedSyncContainer
    from wireup.ioc.types import InjectionResult


current_request: ContextVar[HttpRequest] = ContextVar("wireup_django_request")
async_view_request_container: ContextVar[ScopedAsyncContainer] = ContextVar("wireup_async_view_request_container")
sync_view_request_container: ContextVar[ScopedSyncContainer] = ContextVar("wireup_sync_view_request_container")


@sync_and_async_middleware
def wireup_middleware(  # noqa: D103
    get_response: Callable[[HttpRequest], HttpResponse],
) -> Callable[[HttpRequest], HttpResponse | Awaitable[HttpResponse]]:
    container = _get_base_container()

    if asyncio.iscoroutinefunction(get_response):

        async def async_inner(request: HttpRequest) -> HttpResponse:
            async with container.enter_scope() as scoped:
                container_token = async_view_request_container.set(scoped)
                request_token = current_request.set(request)
                try:
                    return await get_response(request)
                finally:
                    current_request.reset(request_token)
                    async_view_request_container.reset(container_token)

        return async_inner

    def sync_inner(request: HttpRequest) -> HttpResponse:
        with async_container_force_sync_scope(container) as scoped:
            container_token = sync_view_request_container.set(scoped)
            request_token = current_request.set(request)
            try:
                return get_response(request)
            finally:
                current_request.reset(request_token)
                sync_view_request_container.reset(container_token)

    return sync_inner


def _django_request_factory() -> HttpRequest:
    try:
        return current_request.get()
    except LookupError as e:
        msg = (
            "django.http.HttpRequest in wireup is only available during a request. "
            "Did you forget to add 'wireup.integration.django.wireup_middleware' to your list of middlewares?"
        )
        raise WireupError(msg) from e


def get_container() -> ScopedSyncContainer | ScopedAsyncContainer | AsyncContainer:
    """Return the container instance associated with the current django application."""
    try:
        return async_view_request_container.get()
    except LookupError:
        try:
            return sync_view_request_container.get()
        except LookupError:
            return _get_base_container()


def _get_base_container() -> AsyncContainer:
    return apps.get_app_config(WireupConfig.name).container  # type: ignore[reportAttributeAccessIssue]


class WireupConfig(AppConfig):
    """Integrate wireup with Django."""

    name = "wireup"

    def __init__(self, app_name: str, app_module: Any) -> None:
        super().__init__(app_name, app_module)

    def ready(self) -> None:
        integration_settings: WireupSettings = settings.WIREUP

        self.container = wireup.create_async_container(
            service_modules=[
                importlib.import_module(m) if isinstance(m, str) else m for m in integration_settings.service_modules
            ],
            parameters={
                entry: getattr(settings, entry)
                for entry in dir(settings)
                if not entry.startswith("__") and hasattr(settings, entry)
            },
        )
        self.container._registry.register(_django_request_factory, lifetime=ServiceLifetime.SCOPED)
        self.inject_scoped = make_inject_decorator(self.container, get_container)

        if integration_settings.perform_warmup:
            """fix warmup."""

        self._inject(django.urls.get_resolver())

    def _inject(self, resolver: URLResolver) -> None:
        for p in resolver.url_patterns:
            if isinstance(p, URLResolver):
                self._inject(p)
                continue

            if isinstance(p, URLPattern) and p.callback:  # type: ignore[reportUnnecessaryComparison]
                target = p.callback

                if hasattr(p.callback, "view_class") and hasattr(p.callback, "view_initkwargs"):
                    p.callback = self._inject_class_based_view(target)
                else:
                    p.callback = self.inject_scoped(p.callback)
                    self.container._registry.context.remove_dependency_type(target, HttpRequest)

    def _inject_class_based_view(self, callback: Any) -> Any:
        # It is possible in django for one class to serve multiple routes,
        # so this needs to create a new type to disambiguate.
        # see: https://github.com/maldoinc/wireup/issues/53
        wrapped_type = type(f"WireupWrapped{callback.view_class.__name__}", (callback.view_class,), {})
        self.container._registry.register(wrapped_type)

        # This is taken from the django .as_view() method.
        @functools.wraps(callback)
        def view(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            provided_args: InjectionResult = get_container()._callable_get_params_to_inject(wrapped_type)

            this = callback.view_class(**{**callback.view_initkwargs, **provided_args.kwargs})
            this.setup(request, *args, **kwargs)
            if not hasattr(this, "request"):
                raise AttributeError(
                    "{} instance has no 'request' attribute. Did you override "  # noqa: EM103, UP032
                    "setup() and forget to call super()?".format(callback.view_class.__name__)
                )
            return this.dispatch(request, *args, **kwargs)

        return view


@dataclass(frozen=True)
class WireupSettings:
    """Class containing Wireup settings specific to Django."""

    service_modules: list[str | ModuleType]
    """List of modules containing wireup service registrations."""

    perform_warmup: bool = True
    """Setting this to true will cause the container to create
    instances of services at application startup.
    When set to false, services are created on first use.
    """
