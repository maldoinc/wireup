from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

from wireup.errors import UnknownOverrideRequestedError
from wireup.ioc.factory_compiler import CompiledFactory, FactoryCompiler
from wireup.ioc.types import InjectableOverride, Qualifier

if TYPE_CHECKING:
    from collections.abc import Callable


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
        self._original_factories: dict[tuple[type, Qualifier], tuple[CompiledFactory, CompiledFactory]] = {}

    @contextmanager
    def __call__(self, overrides: dict[Any | tuple[Any, Qualifier], Any]) -> Iterator[None]:
        """Override injectables using a dict syntax.

        Supports both simple type keys and tuple keys for qualified injectables:

        ```python
        with container.override({
            UserService: mock_user_service,
            (Database, "primary"): mock_primary_db,
            (Database, "replica"): mock_replica_db,
        }):
            ...
        ```

        :param overrides: Dictionary mapping types or (type, qualifier) tuples to override values.
        """

        override_list: list[InjectableOverride] = []
        for key, new in overrides.items():
            if isinstance(key, tuple):
                target, qualifier = key  # type: ignore[reportUnknownVariableType, unused-ignore]
            else:
                target, qualifier = key, None

            override_list.append(InjectableOverride(target=target, new=new, qualifier=qualifier))  # type: ignore[reportUnknownVariableType, unused-ignore]

        with self.injectables(override_list):
            yield

    def _compiler_override_obj_id(
        self,
        compiler: FactoryCompiler,
        target: type,
        qualifier: Qualifier,
        new: Callable[[Any], Any],
    ) -> None:
        compiler.factories[compiler.get_object_id(target, qualifier)] = CompiledFactory(
            factory=new,
            is_async=False,
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

        self._original_factories[target, qualifier] = (
            self._factory_compiler.factories[obj_id],
            self._scoped_factory_compiler.factories[obj_id],
        )

        def override_factory(_container: Any) -> Any:
            return new

        self._compiler_override_obj_id(
            target=target,
            qualifier=qualifier,
            compiler=self._factory_compiler,
            new=override_factory,
        )
        self._compiler_override_obj_id(
            target=target,
            qualifier=qualifier,
            compiler=self._scoped_factory_compiler,
            new=override_factory,
        )

    def _restore_factory_methods(self, target: type, qualifier: Qualifier | None) -> None:
        """Restore original factory methods after override is removed."""
        if (target, qualifier) not in self._original_factories:
            return

        factory_func, scoped_factory_func = self._original_factories[target, qualifier]
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

        del self._original_factories[target, qualifier]

    def delete(self, target: type, qualifier: Qualifier | None = None) -> None:
        """Clear active override for the `target` injectable."""
        self._restore_factory_methods(target, qualifier)

    def clear(self) -> None:
        """Clear active injectable overrides."""
        for key in self._original_factories:
            self._restore_factory_methods(key[0], key[1])

    @contextmanager
    def injectable(self, target: type, new: Any, qualifier: Qualifier | None = None) -> Iterator[None]:
        """Override the `target` injectable with `new` for the duration of the context manager.

        Deprecated: Use `container.override` instead.

        :param target: The target injectable to override.
        :param qualifier: The qualifier of the injectable to override. Set this if injectable is registered
        with the qualifier parameter set to a value.
        :param new: The new object to be injected instead of `target`.
        """
        warnings.warn(
            "container.override.injectable() is deprecated. Use container.override() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            self.set(target, new, qualifier)
            yield
        finally:
            self.delete(target, qualifier)

    @contextmanager
    def injectables(self, overrides: list[InjectableOverride]) -> Iterator[None]:
        """Override a number of injectables with new for the duration of the context manager.

        Deprecated: Use `container.override` instead.
        """
        warnings.warn(
            "container.override.injectables() is deprecated. Use container.override() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

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
