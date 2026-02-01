from __future__ import annotations

import asyncio
import sys
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Hashable

from wireup.codegen import Codegen
from wireup.errors import WireupError
from wireup.ioc.types import (
    GENERATOR_CALLABLE_TYPES,
    CallableType,
    ConfigInjectionRequest,
    TemplatedString,
)
from wireup.util import format_name

if TYPE_CHECKING:
    from wireup.ioc.container.base_container import BaseContainer
    from wireup.ioc.registry import ContainerRegistry, InjectableFactory


@dataclass(**({"slots": True} if sys.version_info >= (3, 10) else {}))
class CompiledFactory:
    factory: Callable[[BaseContainer], Any]
    is_async: bool


@dataclass(**({"slots": True} if sys.version_info >= (3, 10) else {}))
class FactoryDependencyTarget:
    name: str
    is_config: bool
    config_name: str | TemplatedString | None = None
    dependency_obj_id: int | None = None
    is_async: bool = False


_CONTAINER_SCOPE_ERROR_MSG = (
    "Scope mismatch: Cannot resolve {lifetime} injectable {fmt_klass} "
    "from the root container. "
    "Only Singleton injectables can be resolved without a scope. "
    "To resolve {lifetime} injectables, you must create a scope.\n"
    "See: https://maldoinc.github.io/wireup/latest/lifetimes_and_scopes/"
)

_WIREUP_GENERATED_FACTORY_NAME = "_wireup_factory"
_SENTINEL = object()


class FactoryCompiler:
    def __init__(
        self,
        registry: ContainerRegistry,
        *,
        is_scoped_container: bool,
        concurrent_scoped_access: bool = False,
    ) -> None:
        self._registry = registry
        self._is_scoped_container = is_scoped_container
        self._concurrent_scoped_access = concurrent_scoped_access
        self.factories: dict[int, CompiledFactory] = {}

    @classmethod
    def get_object_id(cls, impl: type, qualifier: Hashable) -> int:
        return hash(impl if qualifier is None else (impl, qualifier))

    def compile(self, copy_singletons_from: FactoryCompiler | None = None) -> None:
        for impl, qualifiers in self._registry.impls.items():
            for qualifier in qualifiers:
                obj_id = FactoryCompiler.get_object_id(impl, qualifier)

                if obj_id in self.factories:
                    continue

                if (
                    copy_singletons_from
                    and (compiled := copy_singletons_from.factories.get(obj_id))
                    and self._registry.lifetime[impl, qualifier] == "singleton"
                ):
                    self.factories[obj_id] = compiled
                    continue

                self.factories[obj_id] = self._compile_and_create_function(
                    self._registry.factories[impl, qualifier],
                    impl,
                    qualifier,
                )

        for interface, impls in self._registry.interfaces.items():
            for qualifier, impl in impls.items():
                obj_id = FactoryCompiler.get_object_id(interface, qualifier)

                if obj_id in self.factories:
                    continue

                if (
                    copy_singletons_from
                    and (compiled := copy_singletons_from.factories.get(obj_id))
                    and self._registry.lifetime[impl, qualifier] == "singleton"
                ):
                    self.factories[obj_id] = compiled
                    continue

                self.factories[obj_id] = self._compile_and_create_function(
                    self._registry.factories[impl, qualifier],
                    interface,
                    qualifier,
                )

    def _get_factory_code(  # noqa: C901, PLR0915
        self,
        factory: InjectableFactory,
        lifetime: str,
        *,
        is_interface: bool,
    ) -> tuple[str, bool, bool]:
        cg = Codegen()

        maybe_async = "async " if factory.is_async else ""
        cg += f"{maybe_async}def {_WIREUP_GENERATED_FACTORY_NAME}(container):"
        cache_created_instance = lifetime != "transient"

        def _generate_factory_body(cg: Codegen) -> None:
            kwargs = ""
            for name, dep in self._registry.dependencies[factory.factory].items():
                if isinstance(dep.annotation, ConfigInjectionRequest):
                    param_value = (
                        str(dep.annotation.config_key)
                        if isinstance(dep.annotation.config_key, TemplatedString)
                        else f'"{dep.annotation.config_key}"'
                    )
                    cg += f"_obj_dep_{name} = parameters.get({param_value})"
                else:
                    if self._registry.is_interface_known(dep.klass):
                        dep_class = self._registry.interface_resolve_impl(dep.klass, dep.qualifier_value)
                        dep_key = dep.klass
                    else:
                        dep_class = dep.klass
                        dep_key = dep.klass

                    maybe_await = "await " if self._registry.factories[dep_class, dep.qualifier_value].is_async else ""
                    dep_hash = FactoryCompiler.get_object_id(dep_key, dep.qualifier_value)
                    cg += f"_obj_dep_{name} = {maybe_await}factories[{dep_hash}].factory(container)"
                kwargs += f"{name}=_obj_dep_{name}, "

            maybe_await = "await " if factory.callable_type == CallableType.COROUTINE_FN else ""

            cg += f"instance = {maybe_await}ORIGINAL_FACTORY({kwargs.strip()})"

            if factory.callable_type in GENERATOR_CALLABLE_TYPES:
                if lifetime == "singleton":
                    cg += "container._global_scope_exit_stack.append(instance)"
                else:
                    cg += "container._current_scope_exit_stack.append(instance)"

                if factory.callable_type == CallableType.GENERATOR:
                    cg += "instance = next(instance)"
                else:
                    cg += "instance = await instance.__anext__()"

            if cache_created_instance:
                cg += "storage[OBJ_ID] = instance"
                if is_interface:
                    cg += "storage[ORIGINAL_OBJ_ID] = instance"

            cg += "return instance"

        with cg.indent():
            if cache_created_instance:
                if lifetime == "singleton":
                    cg += "storage = container._global_scope_objects"
                else:
                    cg += "storage = container._current_scope_objects"

                cg += "if (res := storage.get(OBJ_ID, _SENTINEL)) is not _SENTINEL:"
                with cg.indent():
                    cg += "return res"

                if lifetime == "singleton" or self._concurrent_scoped_access:
                    lock = "_singleton_lock" if lifetime == "singleton" else "container._locks[OBJ_HASH]"

                    if factory.is_async:
                        cg += f"async with {lock}:"
                    else:
                        cg += f"with {lock}:"

                    with cg.indent():
                        # Use Double-Checked locking for factories
                        # See: https://en.wikipedia.org/wiki/Double-checked_locking
                        cg += "if (res := storage.get(OBJ_ID, _SENTINEL)) is not _SENTINEL:"
                        with cg.indent():
                            cg += "return res"

                        _generate_factory_body(cg)
                else:
                    _generate_factory_body(cg)
            else:
                _generate_factory_body(cg)

        return cg.get_source(), factory.is_async, lifetime == "singleton"

    def _compile_and_create_function(
        self, factory: InjectableFactory, impl: type, qualifier: Hashable
    ) -> CompiledFactory:
        obj_id = impl, qualifier
        resolved_obj_id = (
            (self._registry.interface_resolve_impl(impl, qualifier), qualifier)
            if self._registry.is_interface_known(impl)
            else obj_id
        )

        is_interface = self._registry.is_interface_known(impl)

        if is_interface:
            lifetime = self._registry.lifetime[self._registry.interface_resolve_impl(impl, qualifier), qualifier]
        else:
            lifetime = self._registry.lifetime[impl, qualifier]

        # Non-singleton types cannot be resolved from the root container. Return a factory that will simply error.
        if lifetime != "singleton" and not self._is_scoped_container:
            return CompiledFactory(
                factory=FactoryCompiler._create_scope_mismatch_error_factory(impl, qualifier, lifetime),
                is_async=False,
            )

        obj_hash = FactoryCompiler.get_object_id(impl, qualifier)
        source, is_async, needs_global_lock = self._get_factory_code(
            factory,
            lifetime,
            is_interface=is_interface,
        )

        try:
            namespace: dict[str, Any] = {
                "factories": self.factories,
                "ORIGINAL_OBJ_ID": obj_id,
                "OBJ_ID": resolved_obj_id,
                "OBJ_HASH": obj_hash,
                "ORIGINAL_FACTORY": self._registry.factories[resolved_obj_id].factory,
                "TemplatedString": TemplatedString,
                "WireupError": WireupError,
                "_CONTAINER_SCOPE_ERROR_MSG": _CONTAINER_SCOPE_ERROR_MSG,
                "_SENTINEL": _SENTINEL,
                "parameters": self._registry.parameters,
            }

            if needs_global_lock:
                namespace["_singleton_lock"] = asyncio.Lock() if is_async else threading.Lock()

            compiled_code = compile(source, f"<{_WIREUP_GENERATED_FACTORY_NAME}_{obj_id}>", "exec")
            exec(compiled_code, namespace)  # noqa: S102

            return CompiledFactory(factory=namespace[_WIREUP_GENERATED_FACTORY_NAME], is_async=is_async)

        except Exception as e:
            msg = f"Failed to compile generated factory {obj_id}: {e}"
            raise WireupError(msg) from e

    @staticmethod
    def _create_scope_mismatch_error_factory(
        impl: type,
        qualifier: Hashable,
        lifetime: str,
    ) -> Callable[[BaseContainer], Any]:
        def _factory(_: BaseContainer) -> Any:
            msg = _CONTAINER_SCOPE_ERROR_MSG.format(fmt_klass=format_name(impl, qualifier), lifetime=lifetime)
            raise WireupError(msg)

        return _factory
