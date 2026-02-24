from __future__ import annotations

import warnings
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    TypeVar,
    overload,
)

from wireup.errors import (
    UnknownServiceRequestedError,
    WireupError,
)
from wireup.ioc.container.lock_registry import LockRegistry
from wireup.ioc.types import ExitStack  # noqa: TC001  # Used at runtime

if TYPE_CHECKING:
    from wireup.ioc.configuration import ConfigStore
    from wireup.ioc.factory_compiler import FactoryCompiler
    from wireup.ioc.override_manager import OverrideManager
    from wireup.ioc.registry import ContainerRegistry
    from wireup.ioc.types import (
        ContainerObjectIdentifier,
        Qualifier,
    )

T = TypeVar("T")


class BaseContainer:
    __slots__ = (
        "_compiler",
        "_concurrent_scoped_access",
        "_current_scope_exit_stack",
        "_current_scope_objects",
        "_factories",
        "_global_scope_exit_stack",
        "_global_scope_objects",
        "_locks",
        "_override_mgr",
        "_registry",
        "_scoped_compiler",
    )

    def __init__(  # noqa: PLR0913
        self,
        registry: ContainerRegistry,
        override_manager: OverrideManager,
        factory_compiler: FactoryCompiler,
        scoped_compiler: FactoryCompiler,
        global_scope_objects: dict[ContainerObjectIdentifier, Any],
        global_scope_exit_stack: ExitStack,
        current_scope_objects: dict[ContainerObjectIdentifier, Any] | None = None,
        current_scope_exit_stack: ExitStack | None = None,
        *,
        concurrent_scoped_access: bool = False,
    ) -> None:
        self._registry = registry
        self._override_mgr = override_manager
        self._global_scope_objects = global_scope_objects
        self._global_scope_exit_stack = global_scope_exit_stack
        self._current_scope_objects = current_scope_objects
        self._current_scope_exit_stack = current_scope_exit_stack
        self._compiler = factory_compiler
        self._scoped_compiler = scoped_compiler
        self._concurrent_scoped_access = concurrent_scoped_access
        self._factories = self._compiler.factories
        self._locks: LockRegistry | None = LockRegistry() if concurrent_scoped_access else None

    @property
    def params(self) -> ConfigStore:
        """Configuration associated with this container."""
        msg = "Parameters have been renamed to Config. Use `container.config` instead of `container.params`."
        warnings.warn(msg, FutureWarning, stacklevel=2)
        return self._registry.parameters

    @property
    def config(self) -> ConfigStore:
        """Configuration associated with this container."""
        return self._registry.parameters

    @property
    def override(self) -> OverrideManager:
        """Override registered container injectables with new values."""
        return self._override_mgr

    @overload
    def _synchronous_get(self, klass: type[T], qualifier: Qualifier | None = None) -> T: ...
    @overload
    def _synchronous_get(self, klass: Callable[..., T], qualifier: Qualifier | None = None) -> T: ...

    def _synchronous_get(
        self,
        klass: Callable[..., T],
        qualifier: Qualifier | None = None,
    ) -> T | None:
        """Get an instance of the requested type.
        :param qualifier: Qualifier for the class if it was registered with one.
        :param klass: Class of the dependency already registered in the container.
        :return: An instance of the requested object. Always returns an existing instance when one is available.
        """
        obj_id = hash(klass if qualifier is None else (klass, qualifier))

        if compiled_factory := self._factories.get(obj_id):
            if compiled_factory.is_async:
                # If the dependency is async, we cannot call the compiled factory in a synchronous context.
                # However, if it was already instantiated we can return the cached instance.
                cache_key: tuple[type, Qualifier | None] = (klass, qualifier)  # type:ignore[assignment]

                active_override = self._override_mgr._get_active_override(cache_key)
                if active_override.found:
                    return active_override.value  # type:ignore[no-any-return]

                if cache_key in self._global_scope_objects:
                    return self._global_scope_objects[cache_key]  # type:ignore[no-any-return]

                if self._current_scope_objects is not None and cache_key in self._current_scope_objects:
                    return self._current_scope_objects[cache_key]  # type:ignore[no-any-return]

                msg = (
                    f"{klass} is an async dependency and it cannot be created in a synchronous context. "
                    "Create and use an async container via wireup.create_async_container."
                )
                raise WireupError(msg)

            return compiled_factory.factory(self)  # type:ignore[no-any-return]

        raise UnknownServiceRequestedError(klass, qualifier)

    def _recompile(self) -> None:
        """Update internal container state after registry changes"""
        self._compiler.compile()
        self._scoped_compiler.compile(copy_singletons_from=self._compiler)
