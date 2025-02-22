from __future__ import annotations

from wireup.ioc._exit_stack import clean_exit_stack
from wireup.ioc.base_container import BaseContainer


class SyncContainer(BaseContainer):
    get = BaseContainer._synchronous_get

    def close(self) -> None:
        clean_exit_stack(self._global_scope.exit_stack)
