from __future__ import annotations

import contextlib
from typing import AsyncIterator, Iterator

from wireup.ioc._exit_stack import async_clean_exit_stack, clean_exit_stack
from wireup.ioc.container.async_container import AsyncContainer
from wireup.ioc.container.sync_container import SyncContainer
from wireup.ioc.types import ContainerScope


class ScopedContainer(SyncContainer): ...


class ScopedAsyncContainer(AsyncContainer): ...


@contextlib.contextmanager
def enter_scope(container: SyncContainer | AsyncContainer) -> Iterator[ScopedContainer]:
    """Create a new scoped container from the base container provided."""
    scope = ContainerScope()
    scoped_container = ScopedContainer(
        registry=container._registry,
        parameters=container._params,
        overrides=container._overrides,
        global_scope=container._global_scope,
        current_scope=scope,
    )
    try:
        yield scoped_container
    finally:
        clean_exit_stack(scope.exit_stack)


@contextlib.asynccontextmanager
async def enter_async_scope(container: AsyncContainer) -> AsyncIterator[ScopedAsyncContainer]:
    """Create a new scoped container from the base container provided."""
    scope = ContainerScope()
    scoped_container = ScopedAsyncContainer(
        registry=container._registry,
        parameters=container._params,
        overrides=container._overrides,
        global_scope=container._global_scope,
        current_scope=scope,
    )
    try:
        yield scoped_container
    finally:
        await async_clean_exit_stack(scope.exit_stack)
