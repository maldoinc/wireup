"""Django Ninja integration for Wireup dependency injection.

This module provides a decorator that enables Wireup dependency injection
in Django Ninja route handlers. Django Ninja inspects function signatures
to determine request parameters (Body, Query, Path, etc.). Without this
decorator, Wireup-injected services would be incorrectly interpreted as
request parameters, causing Pydantic schema generation errors.

Example:
    from ninja import Router
    from wireup import Injected
    from wireup.integration.django.ninja import inject

    router = Router()

    @router.post("/items/")
    @inject
    def create_item(
        request,
        data: ItemSchema,
        service: Injected[ItemService],
    ):
        return service.create(data)
"""

from typing import Any, Callable, TypeVar

from wireup._decorators import inject_from_container_unchecked
from wireup.integration.django import get_request_container
from wireup.ioc.validation import hide_annotated_names

__all__ = ["inject"]

F = TypeVar("F", bound=Callable[..., Any])


def inject(func: F) -> F:
    """Decorator for Django Ninja views that enables Wireup dependency injection.

    Django Ninja inspects function signatures to determine how to parse request
    parameters. This decorator hides Wireup-injectable parameters from Ninja's
    introspection and resolves them from the container at runtime.

    The decorator:
    1. Identifies parameters annotated with ``Injected[T]`` or ``Annotated[T, Inject()]``
    2. Modifies the function's ``__signature__`` to exclude those parameters
    3. Resolves dependencies from the Wireup scoped container at request time

    Note:
        Place ``@inject`` below ``@router.*`` decorators::

            @router.post("/items/")
            @inject  # <- inject goes here
            def create_item(request, service: Injected[ItemService]):
                ...

    Args:
        func: The Django Ninja route handler function to decorate.

    Returns:
        The decorated function with Wireup injection enabled.

    Example:
        Basic usage with a service dependency::

            from ninja import Router
            from wireup import Injected
            from wireup.integration.django.ninja import inject

            from myapp.services import ItemService
            from myapp.schemas import ItemSchema, ItemResponse

            router = Router()

            @router.post("/items/", response=ItemResponse)
            @inject
            def create_item(
                request,
                data: ItemSchema,
                service: Injected[ItemService],
            ) -> ItemResponse:
                item = service.create(data)
                return ItemResponse.from_orm(item)

        With parameter injection::

            from typing import Annotated
            from wireup import Inject, Injected
            from wireup.integration.django.ninja import inject

            @router.get("/config/")
            @inject
            def get_config(
                request,
                debug: Annotated[bool, Inject(param="DEBUG")],
                service: Injected[ConfigService],
            ):
                return {"debug": debug, "config": service.get_all()}
    """
    # Modify __signature__ and __annotations__ to hide injectable params from Ninja.
    # This also stores the original injectable params in __wireup_names__ for later use.
    hide_annotated_names(func)

    # Wrap the function with Wireup injection logic.
    # inject_from_container_unchecked will use __wireup_names__ to determine what to inject.
    return inject_from_container_unchecked(get_request_container)(func)  # type: ignore[return-value]
