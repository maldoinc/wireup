import contextlib
from typing import Iterator

from wireup.ioc._exit_stack import clean_exit_stack
from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.types import ContainerScope


class BareSyncContainer(BaseContainer):
    get = BaseContainer._synchronous_get

    def close(self) -> None:
        clean_exit_stack(self._global_scope.exit_stack)


class ScopedSyncContainer(BareSyncContainer): ...


class SyncContainer(BareSyncContainer):
    @contextlib.contextmanager
    def enter_scope(self) -> Iterator[ScopedSyncContainer]:
        scope = ContainerScope()
        scoped_container = ScopedSyncContainer(
            registry=self._registry,
            parameters=self._params,
            overrides=self._overrides,
            global_scope=self._global_scope,
            current_scope=scope,
        )
        try:
            yield scoped_container
        finally:
            clean_exit_stack(scope.exit_stack)
