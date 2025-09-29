from typing import Callable, Any

from wireup._decorators import inject_from_container_unchecked
from wireup.integration.django.apps import get_request_container


def inject(func: Callable[..., Any]) -> Callable[..., Any]:
    return inject_from_container_unchecked(get_request_container)(func)
