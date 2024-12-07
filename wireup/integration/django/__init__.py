from contextvars import ContextVar
from dataclasses import dataclass
from types import ModuleType
from typing import Callable, List, NewType, Union

from django.http import HttpRequest, HttpResponse

from wireup.errors import WireupError

current_request: ContextVar[HttpRequest] = ContextVar("wireup_django_request")


def wireup_middleware(get_response: Callable[[HttpRequest], HttpResponse]) -> Callable[[HttpRequest], HttpResponse]:  # noqa: D103
    def _inner(request: HttpRequest) -> HttpResponse:
        token = current_request.set(request)
        try:
            return get_response(request)
        finally:
            current_request.reset(token)

    return _inner


CurrentHttpRequest = NewType("CurrentHttpRequest", HttpRequest)


def django_request_factory() -> HttpRequest:  # noqa: D103
    try:
        return current_request.get()
    except LookupError as e:
        msg = (
            "django.http.HttpRequest in wireup is only available during a request. "
            "Did you forget to add 'wireup.integration.django.wireup_middleware' to your list of middlewares?"
        )
        raise WireupError(msg) from e


@dataclass(frozen=True)
class WireupSettings:
    """Class containing Wireup settings specific to Django."""

    service_modules: List[Union[str, ModuleType]]
    """List of modules containing wireup service registrations."""

    perform_warmup: bool = True
    """Setting this to true will cause the container to create
    instances of services at application startup.
    When set to false, services are created on first use.
    """
