from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

from wireup.errors import UnknownOverrideRequestedError
from wireup.ioc.factory_compiler import CompiledFactory, FactoryCompiler

if TYPE_CHECKING:
    from collections.abc import Callable

    from wireup.ioc.types import Qualifier, ServiceOverride


class OverrideManager:
    """Enables overriding of services registered with the container."""

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
        """Override the `target` service with `new`.

        Future requests to inject `target` will result in `new` being injected.

        :param target: The target service to override.
        :param qualifier: The qualifier of the service to override. Set this if service is registered
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
        """Clear active override for the `target` service."""
        self._restore_factory_methods(target, qualifier)

    def clear(self) -> None:
        """Clear active service overrides."""
        for key in self._original_factories:
            self._restore_factory_methods(key[0], key[1])

    @contextmanager
    def service(self, target: type, new: Any, qualifier: Qualifier | None = None) -> Iterator[None]:
        """Override the `target` service with `new` for the duration of the context manager.

        Future requests to inject `target` will result in `new` being injected.

        :param target: The target service to override.
        :param qualifier: The qualifier of the service to override. Set this if service is registered
        with the qualifier parameter set to a value.
        :param new: The new object to be injected instead of `target`.
        """
        try:
            self.set(target, new, qualifier)
            yield
        finally:
            self.delete(target, qualifier)

    @contextmanager
    def services(self, overrides: list[ServiceOverride]) -> Iterator[None]:
        """Override a number of services with new for the duration of the context manager."""
        try:
            for override in overrides:
                self.set(override.target, override.new, override.qualifier)
            yield
        finally:
            for override in overrides:
                self.delete(override.target, override.qualifier)
