from typing import Callable, Any

from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.integration.django.apps import get_request_container


def inject(func: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(func, "__wireup_marked__", False):
        raise WireupError(
            f"@inject decorator applied multiple times to {func.__module__}.{func.__name__}. "
            "Apply it only once."
        )
    
    setattr(func, "__wireup_marked__", True)
    return inject_from_container_unchecked(get_request_container)(func)
