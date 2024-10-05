from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

import django
import django.urls
from django.apps import AppConfig
from django.conf import settings
from django.urls import URLPattern, URLResolver

import wireup

if TYPE_CHECKING:
    from django.http import HttpRequest

    from wireup.integration.django import WireupSettings


class WireupConfig(AppConfig):
    """Integrate wireup with Django."""

    name = "wireup.integration.django"

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
            nonlocal self
            autowired_args = self.container._DependencyContainer__callable_get_params_to_inject(callback.view_class)  # type: ignore[reportAttributeAccessIssue] # noqa: SLF001

            self = callback.view_class(**{**callback.view_initkwargs, **autowired_args})
            self.setup(request, *args, **kwargs)
            if not hasattr(self, "request"):
                raise AttributeError(
                    "{} instance has no 'request' attribute. Did you override "  # noqa: EM103, UP032
                    "setup() and forget to call super()?".format(callback.view_class.__name__)
                )
            return self.dispatch(request, *args, **kwargs)

        return view
