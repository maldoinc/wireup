from __future__ import annotations

import asyncio
import functools
from typing import TYPE_CHECKING, Any

from wireup.ioc._exit_stack import async_clean_exit_stack, clean_exit_stack

if TYPE_CHECKING:
    from collections.abc import Callable

    from wireup.ioc.base_container import BaseContainer
    from wireup.ioc.scoped_container import ScopedAsyncContainer, ScopedContainer


def make_inject_decorator(
    container: BaseContainer,
    scoped_container_supplier: Callable[[], ScopedContainer | ScopedAsyncContainer] | None = None,
) -> Callable[..., Any]:
    """Provide known dependencies to the applied function.

    :param container: The base container instance. This is what you created via `wireup.create_container`.
    :param scoped_container_supplier: A callable with no arguments that returns the current scoped container
    instance. Setting this will enable the container to inject scoped dependencies otno the target.
    """

    # Exit stack needs to be cleaned in case the container handling injection is not a scoped one.
    def _decorator(target: Callable[..., Any]) -> Callable[..., Any]:
        container._registry.target_init_context(target)

        if asyncio.iscoroutinefunction(target):

            @functools.wraps(target)
            async def _inject_async_target(*args: Any, **kwargs: Any) -> Any:
                c = scoped_container_supplier() if scoped_container_supplier else container
                res = await c._async_callable_get_params_to_inject(target)
                try:
                    return await target(*args, **{**kwargs, **res.kwargs})
                finally:
                    if res.exit_stack:
                        await async_clean_exit_stack(res.exit_stack)

            return _inject_async_target

        @functools.wraps(target)
        def _inject_target(*args: Any, **kwargs: Any) -> Any:
            c = scoped_container_supplier() if scoped_container_supplier else container
            res = c._callable_get_params_to_inject(target)
            try:
                return target(*args, **{**kwargs, **res.kwargs})
            finally:
                if res.exit_stack:
                    clean_exit_stack(res.exit_stack)

        return _inject_target

    return _decorator
