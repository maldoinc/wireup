from __future__ import annotations

from typing import TYPE_CHECKING, Callable, TypeVar, overload

from typing_extensions import Self

from wireup.errors import UnknownServiceRequestedError
from wireup.ioc._exit_stack import async_clean_exit_stack
from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.container.sync_container import ScopedSyncContainer

if TYPE_CHECKING:
    from types import TracebackType

    from wireup.ioc.types import ContainerObjectIdentifier, Qualifier

T = TypeVar("T")


class BareAsyncContainer(BaseContainer):
    @overload
    async def get(self, klass: type[T], qualifier: Qualifier | None = None) -> T: ...
    @overload
    async def get(self, klass: Callable[..., T], qualifier: Qualifier | None = None) -> T: ...

    async def get(
        self,
        klass: Callable[..., T] | None,
        qualifier: Qualifier | None = None,
    ) -> T | None:
        """Get an instance of the requested type.

        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        obj_id: ContainerObjectIdentifier = klass if qualifier is None else (klass, qualifier)  # type: ignore[assignment]

        if compiled_factory := self._factories.get(obj_id):
            res = compiled_factory.factory(self)

            return await res if compiled_factory.is_async else res  # type:ignore[no-any-return]

        raise UnknownServiceRequestedError(klass, qualifier)

    async def close(self) -> None:
        """Close the container and clean up all resources."""
        await async_clean_exit_stack(self._global_scope_exit_stack)


class ScopedAsyncContainer(BareAsyncContainer):
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        _exc_tb: TracebackType | None = None,
    ) -> None:
        if self._current_scope_exit_stack:
            await async_clean_exit_stack(self._current_scope_exit_stack, exc_val=exc_val, exc_tb=_exc_tb)


class AsyncContainer(BareAsyncContainer):
    def enter_scope(self) -> ScopedAsyncContainer:
        """Enter a new scope.

        The returned scope context manager controls the lifetime of scoped dependencies.
        It must be used as an async context manager: `async with container.enter_scope() as scope:`.

        Scoped dependencies are created once per scope and shared within that scope.
        They are discarded when the context manager exits.

        See the documentation for more details:
        https://maldoinc.github.io/wireup/latest/lifetimes_and_scopes/#working-with-scopes
        """
        return ScopedAsyncContainer(
            registry=self._registry,
            override_manager=self._override_mgr,
            global_scope_objects=self._global_scope_objects,
            global_scope_exit_stack=self._global_scope_exit_stack,
            current_scope_objects={},
            current_scope_exit_stack=[],
            factory_compiler=self._scoped_compiler,
            scoped_compiler=self._scoped_compiler,
            concurrent_scoped_access=self._concurrent_scoped_access,
        )


def async_container_force_sync_scope(container: AsyncContainer) -> ScopedSyncContainer:
    """Force an async container to enter a synchronous scope.

    This can be useful when you need to inject synchronous functions
    in an environment that supports both sync and async.
    """
    return ScopedSyncContainer(
        registry=container._registry,
        override_manager=container._override_mgr,
        global_scope_objects=container._global_scope_objects,
        global_scope_exit_stack=container._global_scope_exit_stack,
        current_scope_objects={},
        current_scope_exit_stack=[],
        factory_compiler=container._scoped_compiler,
        scoped_compiler=container._scoped_compiler,
        concurrent_scoped_access=container._concurrent_scoped_access,
    )
