from __future__ import annotations

import asyncio
import functools
from contextlib import AsyncExitStack, ExitStack
from typing import TYPE_CHECKING, Any

from wireup.ioc.container.async_container import AsyncContainer, async_container_force_sync_scope
from wireup.ioc.container.sync_container import SyncContainer

if TYPE_CHECKING:
    from collections.abc import Callable

    from wireup.ioc.container.async_container import ScopedAsyncContainer
    from wireup.ioc.container.sync_container import ScopedSyncContainer


def inject_from_container(
    container: SyncContainer | AsyncContainer,
    scoped_container_supplier: Callable[[], ScopedSyncContainer | ScopedAsyncContainer] | None = None,
) -> Callable[..., Any]:
    """Provide known dependencies to the applied function.

    :param container: The base container instance. This is what you created via `wireup.create_container`.
    :param scoped_container_supplier: A callable with no arguments that returns the current scoped container
    instance. If provided, the decorator will use it to create scoped dependencies. If not provided then the
    container will enter a scope by itself. You should provide a scoped_container_supplier if you want to directly
    manage yourself when the container will enter or exit the scope. When using with web frameworks you may want to
    enter the scope as the first thing on a request in a middleware so that other middlewares can also access the
    scoped container if required.
    """

    # Exit stack needs to be cleaned in case the container handling injection is not a scoped one.
    def _decorator(target: Callable[..., Any]) -> Callable[..., Any]:
        container._registry.target_init_context(target)

        if asyncio.iscoroutinefunction(target):

            @functools.wraps(target)
            async def _inject_async_target(*args: Any, **kwargs: Any) -> Any:
                if isinstance(container, SyncContainer):
                    msg = (
                        "Sync container cannot perform injectio on async targets. "
                        "Please create an async container via wireup.create_async_container."
                    )
                    raise TypeError(msg)

                async with AsyncExitStack() as cm:
                    scoped_container = (
                        scoped_container_supplier()
                        if scoped_container_supplier
                        else await cm.enter_async_context(container.enter_scope())
                    )

                    res = await scoped_container._async_callable_get_params_to_inject(target)
                    return await target(*args, **{**kwargs, **res.kwargs})

            return _inject_async_target

        @functools.wraps(target)
        def _inject_target(*args: Any, **kwargs: Any) -> Any:
            with ExitStack() as cm:
                scoped_container = (
                    scoped_container_supplier()
                    if scoped_container_supplier
                    else cm.enter_context(
                        container.enter_scope()
                        if isinstance(container, SyncContainer)
                        else async_container_force_sync_scope(container)
                    )
                )

                res = scoped_container._callable_get_params_to_inject(target)
                return target(*args, **{**kwargs, **res.kwargs})

        return _inject_target

    return _decorator
