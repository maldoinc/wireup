from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings

from wireup import container, warmup_container

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse


class WireupMiddleware:
    """Django middleware class which performs autowiring on views.

    Using this eliminates the need to decorate views with `@container.autowire`.
    """

    def __init__(self, get_response: Callable[..., HttpResponse]) -> None:
        self.__boot_container()
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:  # noqa: D102
        return self.get_response(request)

    def process_view(
        self, request: HttpRequest, view_func: Callable[..., HttpResponse], args: Any, kwargs: Any
    ) -> HttpResponse:
        """Perform autowiring on django views before processing the request."""
        return container.autowire(view_func)(request, *args, **kwargs)

    @staticmethod
    def __boot_container() -> None:
        service_modules = getattr(settings, "WIREUP_SERVICE_MODULES", [])

        for entry in dir(settings):
            if not entry.startswith("__") and hasattr(settings, entry):
                container.params.put(entry, getattr(settings, entry))

        warmup_container(container, service_modules)
