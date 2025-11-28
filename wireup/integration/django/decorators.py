from typing import Any, Callable

from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.integration.django.apps import get_request_container


def inject(func: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(func, "__wireup_marked__", False):
        msg = f"@inject decorator applied multiple times to {func.__module__}.{func.__name__}. Apply it only once."
        raise WireupError(msg)

    func.__wireup_marked__ = True  # type: ignore[attr-defined]
    return inject_from_container_unchecked(get_request_container)(func)
