from __future__ import annotations

from wireup.ioc._exit_stack import async_clean_exit_stack
from wireup.ioc.base_container import BaseContainer


class AsyncContainer(BaseContainer):
    get = BaseContainer._async_get
    get_dependency_sync = BaseContainer._get

    async def close(self) -> None:
        await async_clean_exit_stack(self._global_scope.exit_stack)
