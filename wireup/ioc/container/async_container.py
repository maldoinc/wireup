from typing_extensions import Self

from wireup.ioc._exit_stack import async_clean_exit_stack
from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.container.sync_container import ScopedSyncContainer


class BareAsyncContainer(BaseContainer):
    get = BaseContainer._async_get

    async def close(self) -> None:
        await async_clean_exit_stack(self._global_scope.exit_stack)


class ScopedAsyncContainer(BareAsyncContainer):
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._current_scope_exit_stack:
            await async_clean_exit_stack(self._current_scope_exit_stack)


class AsyncContainer(BareAsyncContainer):
    def enter_scope(self) -> ScopedAsyncContainer:
        return ScopedAsyncContainer(
            registry=self._registry,
            parameters=self._params,
            override_manager=self._override_mgr,
            global_scope=self._global_scope,
            current_scope_objects={},
            current_scope_exit_stack=[],
        )


def async_container_force_sync_scope(container: AsyncContainer) -> ScopedSyncContainer:
    """Force an async container to enter a synchronous scope.

    This can be useful when you need to inject synchronous functions
    in an environment that supports both sync and async.
    """
    return ScopedSyncContainer(
        registry=container._registry,
        parameters=container._params,
        override_manager=container._override_mgr,
        global_scope=container._global_scope,
        current_scope_objects={},
        current_scope_exit_stack=[],
    )
