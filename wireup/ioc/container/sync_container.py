from typing_extensions import Self

from wireup.ioc._exit_stack import clean_exit_stack
from wireup.ioc.container.base_container import BaseContainer


class BareSyncContainer(BaseContainer):
    get = BaseContainer._synchronous_get

    def close(self) -> None:
        clean_exit_stack(self._global_scope.exit_stack)


class ScopedSyncContainer(BareSyncContainer):
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        clean_exit_stack(self._current_scope_exit_stack)


class SyncContainer(BareSyncContainer):
    def enter_scope(self) -> ScopedSyncContainer:
        return ScopedSyncContainer(
            registry=self._registry,
            parameters=self._params,
            override_manager=self._override_mgr,
            global_scope=self._global_scope,
            current_scope_objects={},
            current_scope_exit_stack=[],
        )
