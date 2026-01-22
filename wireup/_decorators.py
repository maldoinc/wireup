from __future__ import annotations

import contextlib
import functools
import inspect
from contextlib import AsyncExitStack, ExitStack
from typing import TYPE_CHECKING, Any, Callable

import wireup
import wireup.ioc
import wireup.ioc.util
from wireup.errors import WireupError
from wireup.ioc.container.async_container import AsyncContainer, ScopedAsyncContainer, async_container_force_sync_scope
from wireup.ioc.container.sync_container import SyncContainer
from wireup.ioc.types import AnnotatedParameter, ConfigInjectionRequest
from wireup.ioc.util import (
    get_inject_annotated_parameters,
    get_valid_injection_annotated_parameters,
)

if TYPE_CHECKING:
    from wireup.ioc.container.sync_container import ScopedSyncContainer


def inject_from_container_unchecked(
    scoped_container_supplier: Callable[[], ScopedSyncContainer | ScopedAsyncContainer],
    *,
    hide_annotated_names: bool = False,
) -> Callable[..., Any]:
    """Inject dependencies into the decorated function. The "unchecked" part of the name refers to the fact that
    this cannot perform validation on the parameters to inject on module import time due to the absence of a container
    instance."""

    def _decorator(target: Callable[..., Any]) -> Callable[..., Any]:
        return inject_from_container_util(
            target=target,
            names_to_inject=get_inject_annotated_parameters(target),
            container=None,
            scoped_container_supplier=scoped_container_supplier,
            middleware=None,
            hide_annotated_names=hide_annotated_names,
        )

    return _decorator


def inject_from_container(
    container: SyncContainer | AsyncContainer,
    scoped_container_supplier: Callable[[], ScopedSyncContainer | ScopedAsyncContainer] | None = None,
    middleware: Callable[
        [ScopedSyncContainer | ScopedAsyncContainer, tuple[Any, ...], dict[str, Any]],
        contextlib.AbstractContextManager[None],
    ]
    | None = None,
    *,
    hide_annotated_names: bool = False,
) -> Callable[..., Any]:
    """Inject dependencies into the decorated function based on annotations. Wireup containers will
    attempt to provide only parameters annotated with `Inject`.

    See the documentation for more details:
    https://maldoinc.github.io/wireup/latest/function_injection/

    :param container: The root container created via `wireup.create_sync_container` or
        `wireup.create_async_container`.
    :param scoped_container_supplier: An optional callable that returns the current scoped container instance.
        If provided, it will be used to create scoped dependencies. If not provided, the container will automatically
        enter a scope. Provide a scoped_container_supplier if you need to manage the container's scope manually.
    :param middleware: A context manager that wraps the execution of the target function.
    :param hide_annotated_names: If True, the parameters annotated with Wireup annotations will be removed from the
        signature of the decorated function.
    """

    def _decorator(target: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(target) and isinstance(container, SyncContainer):
            msg = (
                "Sync container cannot perform injection on async targets. "
                "Create an async container via wireup.create_async_container."
            )
            raise WireupError(msg)

        return inject_from_container_util(
            target=target,
            names_to_inject=get_valid_injection_annotated_parameters(container, target),
            container=container,
            scoped_container_supplier=scoped_container_supplier,
            middleware=middleware,
            hide_annotated_names=hide_annotated_names,
        )

    return _decorator


def inject_from_container_util(  # noqa: C901, PLR0913
    target: Callable[..., Any],
    names_to_inject: dict[str, AnnotatedParameter],
    container: SyncContainer | AsyncContainer | None,
    scoped_container_supplier: Callable[[], ScopedSyncContainer | ScopedAsyncContainer] | None = None,
    middleware: Callable[
        [ScopedSyncContainer | ScopedAsyncContainer, tuple[Any, ...], dict[str, Any]],
        contextlib.AbstractContextManager[None],
    ]
    | None = None,
    *,
    hide_annotated_names: bool = False,
) -> Callable[..., Any]:
    if not (container or scoped_container_supplier):
        msg = "Container or scoped_container_supplier must be provided for injection."
        raise WireupError(msg)

    if not names_to_inject:
        return target

    if inspect.iscoroutinefunction(target):

        @functools.wraps(target)
        async def _inject_async_target(*args: Any, **kwargs: Any) -> Any:
            async with AsyncExitStack() as cm:
                if scoped_container_supplier:
                    scoped_container = scoped_container_supplier()
                elif container:
                    scoped_container = await cm.enter_async_context(container.enter_scope())  # type: ignore[reportArgumentType, arg-type, unused-ignore]
                else:
                    msg = "scoped_container_supplier or container must be provided for injection."
                    raise ValueError(msg)

                if middleware:
                    cm.enter_context(middleware(scoped_container, args, kwargs))

                injected_names = {
                    name: scoped_container.config.get(param.annotation.config_key)
                    if isinstance(param.annotation, ConfigInjectionRequest)
                    else await scoped_container.get(param.klass, qualifier=param.qualifier_value)
                    for name, param in names_to_inject.items()
                    if param.annotation
                }

                return await target(*args, **{**kwargs, **injected_names})

        res = _inject_async_target
    else:

        @functools.wraps(target)
        def _inject_target(*args: Any, **kwargs: Any) -> Any:
            with ExitStack() as cm:
                if scoped_container_supplier:
                    scoped_container = scoped_container_supplier()
                elif container:
                    scoped_container = cm.enter_context(
                        container.enter_scope()
                        if isinstance(container, SyncContainer)
                        else async_container_force_sync_scope(container)
                    )
                else:
                    msg = "scoped_container_supplier or container must be provided for injection."
                    raise ValueError(msg)

                if middleware:
                    cm.enter_context(middleware(scoped_container, args, kwargs))

                get = scoped_container._synchronous_get

                injected_names = {
                    name: scoped_container.config.get(param.annotation.config_key)
                    if isinstance(param.annotation, ConfigInjectionRequest)
                    else get(param.klass, qualifier=param.qualifier_value)
                    for name, param in names_to_inject.items()
                    if param.annotation
                }
                return target(*args, **{**kwargs, **injected_names})

        res = _inject_target

    if hide_annotated_names:
        wireup.ioc.util.hide_annotated_names(res)

    return res
