from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

import django
import django.urls
from django.apps import AppConfig, apps
from django.conf import settings
from django.urls import URLPattern, URLResolver

import wireup
from wireup import DependencyContainer

if TYPE_CHECKING:
    from django.http import HttpRequest

    from wireup.integration.django import WireupSettings


class WireupConfig(AppConfig):
    """Integrate wireup with Django."""

    name = "wireup"

    def __init__(self, app_name: str, app_module: Any | None) -> None:
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

        if integration_settings.perform_warmup:
            self.container.warmup()

        self._autowire(django.urls.get_resolver())

    def _autowire(self, resolver: URLResolver) -> None:
        for p in resolver.url_patterns:
            if isinstance(p, URLResolver):
                self._autowire(p)
                return

            if isinstance(p, URLPattern) and p.callback:
                if hasattr(p.callback, "view_class") and hasattr(p.callback, "view_initkwargs"):
                    p.callback = self._autowire_class_based_view(p.callback)
                else:
                    p.callback = self.container.autowire(p.callback)

    def _autowire_class_based_view(self, callback: Any) -> Any:
        self.container.register(callback.view_class)

        # This is taken from the django .as_view() method.
        def view(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            autowired_args = self.container._DependencyContainer__callable_get_params_to_inject(callback.view_class)  # type: ignore[reportAttributeAccessIssue] # noqa: SLF001

            this = callback.view_class(**{**callback.view_initkwargs, **autowired_args})
            this.setup(request, *args, **kwargs)
            if not hasattr(this, "request"):
                raise AttributeError(
                    "{} instance has no 'request' attribute. Did you override "  # noqa: EM103, UP032
                    "setup() and forget to call super()?".format(callback.view_class.__name__)
                )
            return this.dispatch(request, *args, **kwargs)

        return view


def get_container() -> DependencyContainer:
    """Return the container instance associated with the current django application."""
    return apps.get_app_config(WireupConfig.name).container  # type: ignore[reportAttributeAccessIssue]
