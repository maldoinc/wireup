from typing import Any, Callable

from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.integration.django.apps import get_request_container
from wireup.ioc.util import hide_annotated_names


def inject(func: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(func, "__wireup_marked__", False):
        msg = f"@inject decorator applied multiple times to {func.__module__}.{func.__name__}. Apply it only once."
        raise WireupError(msg)

    # Modify __signature__ and __annotations__ to hide injectable params (useful for packages like django-ninja)
    # This also stores the original injectable params in __wireup_names__ for later use.
    hide_annotated_names(func)

    func.__wireup_marked__ = True  # type: ignore[attr-defined]
    return inject_from_container_unchecked(get_request_container)(func)
