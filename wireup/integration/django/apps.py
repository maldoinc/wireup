import importlib
from typing import TYPE_CHECKING, Any

import django
import django.urls
from django.apps import AppConfig, apps
from django.conf import settings
from django.http import HttpRequest
from django.urls import URLPattern, URLResolver

import wireup
from wireup import DependencyContainer
from wireup.integration.django import django_request_factory
from wireup.ioc._exit_stack import clean_exit_stack
from wireup.ioc.types import ServiceLifetime

if TYPE_CHECKING:
    from wireup.integration.django import WireupSettings
    from wireup.ioc.dependency_container import _InjectionResult


class WireupConfig(AppConfig):
    """Integrate wireup with Django."""

    name = "wireup"

    def __init__(self, app_name: str, app_module: Any) -> None:
        super().__init__(app_name, app_module)

    def ready(self) -> None:
        integration_settings: WireupSettings = settings.WIREUP

        self.container = wireup.create_container(
            service_modules=[
                importlib.import_module(m) if isinstance(m, str) else m for m in integration_settings.service_modules
            ],
            parameters={
                entry: getattr(settings, entry)
                for entry in dir(settings)
                if not entry.startswith("__") and hasattr(settings, entry)
            },
        )
        self.container.register(django_request_factory, lifetime=ServiceLifetime.TRANSIENT)

        if integration_settings.perform_warmup:
            self.container.warmup()

        self._autowire(django.urls.get_resolver())

    def _autowire(self, resolver: URLResolver) -> None:
        for p in resolver.url_patterns:
            if isinstance(p, URLResolver):
                self._autowire(p)
                return

            if isinstance(p, URLPattern) and p.callback:
                target = p.callback

                if hasattr(p.callback, "view_class") and hasattr(p.callback, "view_initkwargs"):
                    p.callback = self._autowire_class_based_view(target)
                else:
                    p.callback = self.container.autowire(target)
                    self.container._registry.context.remove_dependency_type(target, HttpRequest)  # type: ignore[reportPrivateUsage]  # noqa: SLF001

    def _autowire_class_based_view(self, callback: Any) -> Any:
        self.container.register(callback.view_class)

        # This is taken from the django .as_view() method.
        def view(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            autowired_args: _InjectionResult = self.container._DependencyContainer__callable_get_params_to_inject(  # type: ignore[reportAttributeAccessIssue]  # noqa: SLF001
                callback.view_class
            )

            this = callback.view_class(**{**callback.view_initkwargs, **autowired_args.kwargs})
            try:
                this.setup(request, *args, **kwargs)
                if not hasattr(this, "request"):
                    raise AttributeError(
                        "{} instance has no 'request' attribute. Did you override "  # noqa: EM103, UP032
                        "setup() and forget to call super()?".format(callback.view_class.__name__)
                    )
                return this.dispatch(request, *args, **kwargs)
            finally:
                if autowired_args.exit_stack:
                    clean_exit_stack(autowired_args.exit_stack)

        return view


def get_container() -> DependencyContainer:
    """Return the container instance associated with the current django application."""
    return apps.get_app_config(WireupConfig.name).container  # type: ignore[reportAttributeAccessIssue]
