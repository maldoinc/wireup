import functools
from collections.abc import Callable
from typing import Any, TypeVar

from wireup._decorators import inject_from_container, inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.integration.django.apps import get_app_container, get_request_container
from wireup.ioc.util import hide_annotated_names

R = TypeVar("R")


def inject(func: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(func, "__wireup_marked__", False):
        msg = f"@inject decorator applied multiple times to {func.__module__}.{func.__name__}. Apply it only once."
        raise WireupError(msg)

    # Modify __signature__ and __annotations__ to hide injectable params (useful for packages like django-ninja)
    # This also stores the original injectable params in __wireup_names__ for later use.
    hide_annotated_names(func)

    func.__wireup_marked__ = True  # type: ignore[attr-defined]
    return inject_from_container_unchecked(get_request_container)(func)


def inject_app(func: Callable[..., R]) -> Callable[..., R]:
    """Inject dependencies from the Django application container.

    This decorator is intended for non-request Django entry points such as
    management commands, signal handlers, checks, and other app-level callables.
    """
    if getattr(func, "__wireup_marked__", False):
        msg = f"@inject_app decorator applied multiple times to {func.__module__}.{func.__name__}. Apply it only once."
        raise WireupError(msg)

    wrapped: Callable[..., R] | None = None

    @functools.wraps(func)
    def _wrapped(*args: Any, **kwargs: Any) -> R:
        nonlocal wrapped
        if wrapped is None:
            wrapped = inject_from_container(get_app_container())(func)
        return wrapped(*args, **kwargs)

    _wrapped.__wireup_marked__ = True  # type: ignore[attr-defined]
    return _wrapped
