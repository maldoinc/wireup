from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from typing_extensions import ParamSpec

import wireup
import wireup.ioc
import wireup.ioc.util
from wireup._wrapper_compiler import compile_injection_wrapper
from wireup.errors import WireupError
from wireup.ioc.container.sync_container import SyncContainer
from wireup.ioc.util import (
    get_inject_annotated_parameters,
    get_valid_injection_annotated_parameters,
)

if TYPE_CHECKING:
    from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer
    from wireup.ioc.container.sync_container import ScopedSyncContainer
    from wireup.ioc.types import AnnotatedParameter

P = ParamSpec("P")
R = TypeVar("R")


def _ensure_sync_container_target_is_sync(target: Callable[..., object]) -> None:
    if inspect.iscoroutinefunction(target) or inspect.isasyncgenfunction(target):
        msg = (
            "Sync container cannot perform injection on async targets. "
            "Create an async container via wireup.create_async_container."
        )
        raise WireupError(msg)


def inject_from_container_unchecked(
    scoped_container_supplier: Callable[[], ScopedSyncContainer | ScopedAsyncContainer],
    *,
    hide_annotated_names: bool = False,
) -> Callable[[Callable[P, R]], Callable[..., R]]:
    """Inject dependencies into the decorated function. The "unchecked" part of the name refers to the fact that
    this cannot perform validation on the parameters to inject on module import time due to the absence of a container
    instance."""

    def _decorator(target: Callable[P, R]) -> Callable[..., R]:
        return inject_from_container_util(
            target=target,
            names_to_inject=get_inject_annotated_parameters(target),
            container=None,
            scoped_container_supplier=scoped_container_supplier,
            context_creator=None,
            hide_annotated_names=hide_annotated_names,
        )

    return _decorator


def inject_from_container(
    container: SyncContainer | AsyncContainer,
    scoped_container_supplier: Callable[[], ScopedSyncContainer | ScopedAsyncContainer] | None = None,
    _context_creator: dict[Any, str] | None = None,
    *,
    hide_annotated_names: bool = False,
) -> Callable[[Callable[P, R]], Callable[..., R]]:
    """Inject dependencies into the decorated function based on annotations. Wireup containers will
    attempt to provide only parameters annotated with `Inject`.

    See the documentation for more details:
    https://maldoinc.github.io/wireup/latest/function_injection/

    :param container: The root container created via `wireup.create_sync_container` or
        `wireup.create_async_container`.
    :param scoped_container_supplier: An optional callable that returns the current scoped container instance.
        If provided, it will be used to create scoped dependencies. If not provided, the container will automatically
        enter a scope. Provide a scoped_container_supplier if you need to manage the container's scope manually.
    :param hide_annotated_names: If True, the parameters annotated with Wireup annotations will be removed from the
        signature of the decorated function.
    """

    def _decorator(target: Callable[P, R]) -> Callable[..., R]:
        if isinstance(container, SyncContainer):
            _ensure_sync_container_target_is_sync(target)

        return inject_from_container_util(
            target=target,
            names_to_inject=get_valid_injection_annotated_parameters(container, target),
            container=container,
            scoped_container_supplier=scoped_container_supplier,
            context_creator=_context_creator,
            hide_annotated_names=hide_annotated_names,
        )

    return _decorator


def inject_from_container_util(  # noqa: PLR0913
    target: Callable[P, R],
    names_to_inject: dict[str, AnnotatedParameter],
    container: SyncContainer | AsyncContainer | None,
    scoped_container_supplier: Callable[[], ScopedSyncContainer | ScopedAsyncContainer] | None = None,
    context_creator: dict[Any, str] | None = None,
    *,
    hide_annotated_names: bool,
) -> Callable[..., R]:
    if not (container or scoped_container_supplier):
        msg = "Container or scoped_container_supplier must be provided for injection."
        raise WireupError(msg)

    if not names_to_inject:
        return target

    res = compile_injection_wrapper(
        target=target,
        names_to_inject=names_to_inject,
        container=container,
        scoped_container_supplier=scoped_container_supplier,
        context_creator=context_creator,
    )
    wrapped = res

    if hide_annotated_names:
        wireup.ioc.util.hide_annotated_names(wrapped)

    return wrapped
