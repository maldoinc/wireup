from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Hashable

from wireup.codegen import Codegen

from wireup.errors import WireupError
from wireup.ioc.registry import GENERATOR_FACTORY_TYPES, ContainerRegistry, FactoryType
from wireup.ioc.types import ConfigInjectionRequest, TemplatedString
from wireup.util import format_name

if TYPE_CHECKING:
    from wireup.ioc.container.base_container import BaseContainer
    from wireup.ioc.registry import InjectableFactory



@dataclass
class CompiledFactory:
    factory: Callable[[BaseContainer], Any]
    is_async: bool


_CONTAINER_SCOPE_ERROR_MSG = (
    r"Scope mismatch: Cannot resolve {lifetime} injectable {fmt_klass} "
    r"from the root container. "
    r"Only Singleton injectables can be resolved without a scope. "
    r"To resolve {lifetime} injectables, you must create a scope.\n"
    r"See: https://maldoinc.github.io/wireup/latest/lifetimes_and_scopes/"
)

_WIREUP_GENERATED_FACTORY_NAME = "_wireup_factory"
_SENTINEL = object()


class FactoryCompiler:
    def __init__(self, registry: ContainerRegistry, *, is_scoped_container: bool) -> None:
        self._registry = registry
        self._is_scoped_container = is_scoped_container
        self.factories: dict[int, CompiledFactory] = {}

    @classmethod
    def get_object_id(cls, impl: type, qualifier: Hashable) -> int:
        return hash(impl if qualifier is None else (impl, qualifier))

    def compile(self) -> None:
        for impl, qualifiers in self._registry.impls.items():
            for qualifier in qualifiers:
                obj_id = FactoryCompiler.get_object_id(impl, qualifier)

                if obj_id not in self.factories:
                    self.factories[obj_id] = self._compile_and_create_function(
                        self._registry.factories[impl, qualifier],
                        impl,
                        qualifier,
                    )

        for interface, impls in self._registry.interfaces.items():
            for qualifier, impl in impls.items():
                obj_id = FactoryCompiler.get_object_id(interface, qualifier)

                if obj_id not in self.factories:
                    self.factories[obj_id] = self._compile_and_create_function(
                        self._registry.factories[impl, qualifier],
                        interface,
                        qualifier,
                    )

    def _get_factory_code(self, factory: InjectableFactory, impl: type, qualifier: Hashable) -> tuple[str, bool]:  # noqa: C901, PLR0912
        is_interface = self._registry.is_interface_known(impl)
        if is_interface:
            lifetime = self._registry.lifetime[self._registry.interface_resolve_impl(impl, qualifier), qualifier]
        else:
            lifetime = self._registry.lifetime[impl, qualifier]

        cg = Codegen()

        if lifetime != "singleton" and not self._is_scoped_container:
            fmt_map = {
                "fmt_klass": format_name(impl, qualifier),
                "lifetime": lifetime,
            }

            cg += f"def {_WIREUP_GENERATED_FACTORY_NAME}(container):"
            with cg.indent():
                cg += f'msg = "{_CONTAINER_SCOPE_ERROR_MSG.format_map(fmt_map)}"'
                cg += "raise WireupError(msg)"

            return cg.get_source(), False

        maybe_async = "async " if factory.is_async else ""
        cg += f"{maybe_async}def {_WIREUP_GENERATED_FACTORY_NAME}(container):"
        cache_created_instance = lifetime != "transient"

        with cg.indent():
            if cache_created_instance:
                if lifetime == "singleton":
                    cg += "storage = container._global_scope_objects"
                else:
                    cg += "storage = container._current_scope_objects"

                cg += "if (res := storage.get(OBJ_ID, _SENTINEL)) is not _SENTINEL:"
                with cg.indent():
                    cg += "return res"

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
                    else:
                        dep_class = dep.klass

                    maybe_await = "await " if self._registry.factories[dep_class, dep.qualifier_value].is_async else ""
                    dep_hash = FactoryCompiler.get_object_id(dep_class, dep.qualifier_value)
                    cg += f"_obj_dep_{name} = {maybe_await}factories[{dep_hash}].factory(container)"
                kwargs += f"{name}=_obj_dep_{name}, "

            maybe_await = "await " if factory.factory_type == FactoryType.COROUTINE_FN else ""

            cg += f"instance = {maybe_await}ORIGINAL_FACTORY({kwargs.strip()})"

            if factory.factory_type in GENERATOR_FACTORY_TYPES:
                if lifetime == "singleton":
                    cg += "container._global_scope_exit_stack.append(instance)"
                else:
                    cg += "container._current_scope_exit_stack.append(instance)"

                if factory.factory_type == FactoryType.GENERATOR:
                    cg += "instance = next(instance)"
                else:
                    cg += "instance = await instance.__anext__()"

            if cache_created_instance:
                cg += "storage[OBJ_ID] = instance"
                if is_interface:
                    cg += "storage[ORIGINAL_OBJ_ID] = instance"

            cg += "return instance"

        return cg.get_source(), factory.is_async

    def _compile_and_create_function(
        self, factory: InjectableFactory, impl: type, qualifier: Hashable
    ) -> CompiledFactory:
        obj_id = impl, qualifier
        resolved_obj_id = (
            (self._registry.interface_resolve_impl(impl, qualifier), qualifier)
            if self._registry.is_interface_known(impl)
            else obj_id
        )

        source, is_async = self._get_factory_code(factory, impl, qualifier)

        try:
            namespace: dict[str, Any] = {
                "factories": self.factories,
                "ORIGINAL_OBJ_ID": obj_id,
                "OBJ_ID": resolved_obj_id,
                "ORIGINAL_FACTORY": self._registry.factories[resolved_obj_id].factory,
                "TemplatedString": TemplatedString,
                "WireupError": WireupError,
                "_CONTAINER_SCOPE_ERROR_MSG": _CONTAINER_SCOPE_ERROR_MSG,
                "_SENTINEL": _SENTINEL,
                "parameters": self._registry.parameters,
            }

            compiled_code = compile(source, f"<{_WIREUP_GENERATED_FACTORY_NAME}_{obj_id}>", "exec")
            exec(compiled_code, namespace)  # noqa: S102

            return CompiledFactory(factory=namespace[_WIREUP_GENERATED_FACTORY_NAME], is_async=is_async)

        except Exception as e:
            msg = f"Failed to compile generated factory {obj_id}: {e}"
            raise WireupError(msg) from e
