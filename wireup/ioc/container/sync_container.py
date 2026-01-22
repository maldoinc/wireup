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
        """Close the container and clean up all resources."""
        clean_exit_stack(self._global_scope_exit_stack)


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
        """Enter a new scope.

        The returned scope context manager controls the lifetime of scoped dependencies.
        It must be used as a context manager: `with container.enter_scope() as scope:`.

        Scoped dependencies are created once per scope and shared within that scope.
        They are discarded when the context manager exits.

        See the documentation for more details:
        https://maldoinc.github.io/wireup/latest/lifetimes_and_scopes/#working-with-scopes
        """
        return ScopedSyncContainer(
            registry=self._registry,
            override_manager=self._override_mgr,
            global_scope_objects=self._global_scope_objects,
            global_scope_exit_stack=self._global_scope_exit_stack,
            current_scope_objects={},
            current_scope_exit_stack=[],
            factory_compiler=self._scoped_compiler,
            scoped_compiler=self._scoped_compiler,
        )
