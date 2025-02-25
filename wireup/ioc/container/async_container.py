import contextlib
from typing import AsyncIterator

from wireup.ioc._exit_stack import async_clean_exit_stack
from wireup.ioc.container.base_container import BaseContainer
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
