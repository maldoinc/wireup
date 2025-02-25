import contextlib
from typing import AsyncIterator, Iterator

from wireup.ioc._exit_stack import async_clean_exit_stack, clean_exit_stack
from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.container.sync_container import ScopedSyncContainer
from wireup.ioc.types import ContainerScope


class BareAsyncContainer(BaseContainer):
    get = BaseContainer._async_get
    get_dependency_sync = BaseContainer._synchronous_get

    async def close(self) -> None:
        await async_clean_exit_stack(self._global_scope.exit_stack)


class ScopedAsyncContainer(BareAsyncContainer): ...


class AsyncContainer(BareAsyncContainer):
    @contextlib.asynccontextmanager
    async def enter_scope(self) -> AsyncIterator[ScopedAsyncContainer]:
        scope = ContainerScope()
        scoped_container = ScopedAsyncContainer(
            registry=self._registry,
            parameters=self._params,
            overrides=self._overrides,
            global_scope=self._global_scope,
            current_scope=scope,
        )
        try:
            yield scoped_container
        finally:
            await async_clean_exit_stack(scope.exit_stack)


@contextlib.contextmanager
def async_container_force_sync_scope(container: AsyncContainer) -> Iterator[ScopedSyncContainer]:
    """Force an async container to enter a synchronous scope.

    This can be useful when you need to inject synchronous functions
    in an environment that supports both sync and async.
    """
    scope = ContainerScope()
    scoped_container = ScopedSyncContainer(
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
