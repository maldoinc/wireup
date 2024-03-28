from __future__ import annotations

import importlib
import os
from types import ModuleType

import wireup
from wireup import DependencyContainer, warmup_container


class WireupMiddleware:
    """
    Django middleware class which performs autowiring on views.

    Using this eliminates the need to decorate views with `@container.autowire`.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, args, kwargs):
        return wireup.container.autowire(view_func)(request, *args, **kwargs)


def wireup_init_django_integration(
    service_modules: list[ModuleType],
    dependency_container: DependencyContainer = wireup.container,
    config_prefix: str | None = None,
) -> None:
    """
    Initialize the Django integration with the given service modules.

    :param service_modules: A list of python modules where application services reside. These will be loaded to trigger
    container registrations.
    :param dependency_container: The instance of the dependency container.
    The default wireup singleton will be used when this is unset.
    This will be a noop and have no performance penalty for views which do not use the container.
    :param config_prefix: If set to a value all registered configuration will be prefixed with config and be accessible
    via "prefix.config_name". E.g: app.DEBUG.
    """
    settings_module = importlib.import_module(os.environ.get("DJANGO_SETTINGS_MODULE"))

    for entry in dir(settings_module):
        if not entry.startswith("__"):
            dependency_container.params.put(
                entry if not config_prefix else f"{config_prefix}.{entry}",
                getattr(settings_module, entry),
            )

    warmup_container(dependency_container, service_modules or [])
