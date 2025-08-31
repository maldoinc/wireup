from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

from wireup.errors import UnknownOverrideRequestedError
from wireup.ioc.types import AnyCallable

if TYPE_CHECKING:
    from collections.abc import Callable

    from wireup.ioc.container.compiler import FactoryCompiler
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
        self._original_factory_functions: dict[tuple[type, Qualifier], tuple[Any, Any]] = {}

    def _compiler_override_obj_id(
        self, compiler: FactoryCompiler, obj_id: tuple[type, Qualifier], new: AnyCallable
    ) -> None:
        compiler.factories[obj_id].factory = new
        method_name = compiler.get_fn_name(obj_id[0], obj_id[1])
        setattr(compiler, method_name, compiler.factories[obj_id])

    def _compiler_restore_obj_id(
        self, compiler: FactoryCompiler, obj_id: tuple[type, Qualifier], original: Any
    ) -> None:
        compiler.factories[obj_id].factory = original
        method_name = compiler.get_fn_name(obj_id[0], obj_id[1])
        setattr(compiler, method_name, compiler.factories[obj_id])

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

        obj_id = target, qualifier

        self._original_factory_functions[obj_id] = (
            self._factory_compiler.factories[obj_id].factory,
            self._scoped_factory_compiler.factories[obj_id].factory,
        )

        def override_factory(_container: Any) -> Any:
            return new

        self._compiler_override_obj_id(obj_id=obj_id, compiler=self._factory_compiler, new=override_factory)
        self._compiler_override_obj_id(obj_id=obj_id, compiler=self._scoped_factory_compiler, new=override_factory)

    def _restore_factory_methods(self, key: tuple[type, Qualifier]) -> None:
        """Restore original factory methods after override is removed."""
        if key not in self._original_factory_functions:
            return

        factory_func, scoped_factory_func = self._original_factory_functions[key]
        self._compiler_restore_obj_id(compiler=self._factory_compiler, obj_id=key, original=factory_func)
        self._compiler_restore_obj_id(compiler=self._scoped_factory_compiler, obj_id=key, original=scoped_factory_func)

        del self._original_factory_functions[key]

    def delete(self, target: type, qualifier: Qualifier | None = None) -> None:
        """Clear active override for the `target` service."""
        self._restore_factory_methods((target, qualifier))

    def clear(self) -> None:
        """Clear active service overrides."""
        for key in self._original_factory_functions:
            self._restore_factory_methods(key)

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
