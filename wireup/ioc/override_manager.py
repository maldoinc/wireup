from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

from wireup.errors import UnknownOverrideRequestedError
from wireup.ioc.factory_compiler import CompiledFactory, FactoryCompiler

if TYPE_CHECKING:
    from collections.abc import Callable

    from wireup.ioc.types import InjectableOverride, Qualifier


class OverrideManager:
    """Enables overriding of injectables registered with the container."""

    def __init__(
        self,
        is_valid_override: Callable[[type, Qualifier], bool],
        factory_compiler: FactoryCompiler,
        scoped_factory_compiler: FactoryCompiler,
    ) -> None:
        self.__is_valid_override = is_valid_override
        self._factory_compiler = factory_compiler
        self._scoped_factory_compiler = scoped_factory_compiler
        self._original_factories: dict[tuple[type, Qualifier], list[tuple[CompiledFactory, CompiledFactory]]] = {}
        self.active_overrides: dict[tuple[type, Qualifier], list[Any]] = {}

    def _compiler_override_obj_id(
        self,
        compiler: FactoryCompiler,
        target: type,
        qualifier: Qualifier,
        new: Callable[[Any], Any],
        *,
        is_async: bool = False,
    ) -> None:
        compiler.factories[compiler.get_object_id(target, qualifier)] = CompiledFactory(
            factory=new,
            is_async=is_async,
        )

    def _compiler_restore_obj_id(
        self,
        compiler: FactoryCompiler,
        target: type,
        qualifier: Qualifier,
        original: CompiledFactory,
    ) -> None:
        compiler.factories[compiler.get_object_id(target, qualifier)] = original

    def set(self, target: type, new: Any, qualifier: Qualifier | None = None) -> None:
        """Override the `target` injectable with `new`.

        Future requests to inject `target` will result in `new` being injected.

        :param target: The target injectable to override.
        :param qualifier: The qualifier of the injectable to override. Set this if injectable is registered
        with the qualifier parameter set to a value.
        :param new: The new object to be injected instead of `target`.
        """
        if not self.__is_valid_override(target, qualifier):
            raise UnknownOverrideRequestedError(klass=target, qualifier=qualifier)

        obj_id = FactoryCompiler.get_object_id(target, qualifier)

        active_overrides_stack = self.active_overrides.get((target, qualifier), [])
        active_overrides_stack.append(new)
        self.active_overrides[target, qualifier] = active_overrides_stack

        original_factories_stack = self._original_factories.get((target, qualifier), [])
        original_factories_stack.append(
            (
                self._factory_compiler.factories[obj_id],
                self._scoped_factory_compiler.factories[obj_id],
            )
        )
        self._original_factories[target, qualifier] = original_factories_stack

        singleton_factory, scoped_factory = self._original_factories[target, qualifier][-1]
        # When determining the is_async flag check both the singleton and scoped compilers.
        # For scoped lifetimes the singleton compiler has erroring stub factories which are always sync
        # in which case we need to consult the scoped compiler which has the real factories.
        is_async = singleton_factory.is_async or scoped_factory.is_async

        async def async_override_factory(_container: Any) -> Any:
            return new

        def override_factory(_container: Any) -> Any:
            return new

        factory = async_override_factory if is_async else override_factory

        self._compiler_override_obj_id(
            target=target,
            qualifier=qualifier,
            compiler=self._factory_compiler,
            new=factory,
            is_async=is_async,
        )
        self._compiler_override_obj_id(
            target=target,
            qualifier=qualifier,
            compiler=self._scoped_factory_compiler,
            new=factory,
            is_async=is_async,
        )

    def _restore_factory_methods(self, target: type, qualifier: Qualifier | None) -> None:
        """Restore original factory methods after override is removed."""
        if (target, qualifier) not in self._original_factories:
            return

        factory_func, scoped_factory_func = self._original_factories[target, qualifier].pop()

        self._compiler_restore_obj_id(
            compiler=self._factory_compiler,
            target=target,
            qualifier=qualifier,
            original=factory_func,
        )
        self._compiler_restore_obj_id(
            compiler=self._scoped_factory_compiler,
            target=target,
            qualifier=qualifier,
            original=scoped_factory_func,
        )

        if (target, qualifier) in self.active_overrides:
            if len(self.active_overrides[target, qualifier]) == 0:
                del self.active_overrides[target, qualifier]
            else:
                self.active_overrides[target, qualifier].pop()

    def delete(self, target: type, qualifier: Qualifier | None = None) -> None:
        """Clear active override for the `target` injectable."""
        self._restore_factory_methods(target, qualifier)

    def clear(self) -> None:
        """Clear active injectable overrides."""
        self.active_overrides.clear()
        for key in self._original_factories:
            if self._original_factories[key]:
                # Keep original factory only, pop all remaining overrides
                self._original_factories[key] = self._original_factories[key][:1]
                self._restore_factory_methods(key[0], key[1])
        self._original_factories.clear()

    @contextmanager
    def injectable(self, target: type, new: Any, qualifier: Qualifier | None = None) -> Iterator[None]:
        """Override the `target` injectable with `new` for the duration of the context manager.

        Future requests to inject `target` will result in `new` being injected.

        :param target: The target injectable to override.
        :param qualifier: The qualifier of the injectable to override. Set this if injectable is registered
        with the qualifier parameter set to a value.
        :param new: The new object to be injected instead of `target`.
        """
        try:
            self.set(target, new, qualifier)
            yield
        finally:
            self.delete(target, qualifier)

    @contextmanager
    def injectables(self, overrides: list[InjectableOverride]) -> Iterator[None]:
        """Override a number of injectables with new for the duration of the context manager."""
        try:
            for override in overrides:
                self.set(override.target, override.new, override.qualifier)
            yield
        finally:
            for override in overrides:
                self.delete(override.target, override.qualifier)

    @contextmanager
    def service(self, target: type, new: Any, qualifier: Qualifier | None = None) -> Iterator[None]:
        """Override the `target` injectable with `new` for the duration of the context manager.

        Future requests to inject `target` will result in `new` being injected.

        :param target: The target injectable to override.
        :param qualifier: The qualifier of the injectable to override. Set this if injectable is registered
        with the qualifier parameter set to a value.
        :param new: The new object to be injected instead of `target`.
        """
        warnings.warn(
            "Services are now called Injectables. Use container.override.injectable() instead.",
            FutureWarning,
            stacklevel=2,
        )
        with self.injectable(target, new, qualifier):
            yield

    @contextmanager
    def services(self, overrides: list[InjectableOverride]) -> Iterator[None]:
        """Override a number of injectables with new for the duration of the context manager."""
        warnings.warn(
            "Services are now called Injectables. Use container.override.injectables() instead.",
            FutureWarning,
            stacklevel=2,
        )
        with self.injectables(overrides):
            yield
