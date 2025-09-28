from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import Self

from wireup.ioc._exit_stack import clean_exit_stack
from wireup.ioc.container.base_container import BaseContainer

if TYPE_CHECKING:
    from types import TracebackType


class BareSyncContainer(BaseContainer):
    get = BaseContainer._synchronous_get

    def close(self) -> None:
        clean_exit_stack(self._global_scope.exit_stack)


class ScopedSyncContainer(BareSyncContainer):
    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        _exc_tb: TracebackType | None = None,
    ) -> None:
        if self._current_scope_exit_stack:
            clean_exit_stack(self._current_scope_exit_stack, exc_val=exc_val, exc_tb=_exc_tb)


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
