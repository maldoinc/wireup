from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Hashable

from wireup.errors import WireupError
from wireup.ioc.service_registry import GENERATOR_FACTORY_TYPES, FactoryType, ServiceRegistry
from wireup.ioc.types import ParameterWrapper, TemplatedString

if TYPE_CHECKING:
    from wireup.ioc.container.base_container import BaseContainer
    from wireup.ioc.service_registry import ServiceFactory


@dataclass
class CompiledFactory:
    factory: Callable[[BaseContainer], Any]
    is_async: bool


_CONTAINER_SCOPE_ERROR_MSG = (
    "Cannot create 'transient' or 'scoped' lifetime objects from the base container. "
    "Please enter a scope using container.enter_scope. "
    "If you are within a scope, use the scoped container instance to create dependencies."
)
_WIREUP_GENERATED_FACTORY_NAME = "_wireup_factory"


class FactoryCompiler:
    def __init__(self, registry: ServiceRegistry, *, is_scoped_container: bool) -> None:
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

    def _get_factory_code(self, factory: ServiceFactory, impl: type, qualifier: Hashable) -> tuple[str, bool]:  # noqa: C901, PLR0912
        is_interface = self._registry.is_interface_known(impl)
        if is_interface:
            lifetime = self._registry.lifetime[self._registry.interface_resolve_impl(impl, qualifier), qualifier]
        else:
            lifetime = self._registry.lifetime[impl, qualifier]

        if lifetime != "singleton" and not self._is_scoped_container:
            code = f"def {_WIREUP_GENERATED_FACTORY_NAME}(container):\n"
            code += "    raise WireupError(_CONTAINER_SCOPE_ERROR_MSG)\n"

            return code, False

        maybe_async = "async " if factory.is_async else ""
        code = f"{maybe_async}def {_WIREUP_GENERATED_FACTORY_NAME}(container):\n"
        cache_created_instance = lifetime != "transient"

        if cache_created_instance:
            if lifetime == "singleton":
                code += "    storage = container._global_scope_objects\n"
            else:
                code += "    storage = container._current_scope_objects\n"

            code += "    if res := storage.get(OBJ_ID):\n"
            code += "        return res\n"

        kwargs = ""
        for name, dep in self._registry.dependencies[factory.factory].items():
            if isinstance(dep.annotation, ParameterWrapper):
                param_value = (
                    str(dep.annotation.param)
                    if isinstance(dep.annotation.param, TemplatedString)
                    else f'"{dep.annotation.param}"'
                )
                code += f"    _obj_dep_{name} = parameters.get({param_value})\n"
            else:
                if self._registry.is_interface_known(dep.klass):
                    dep_class = self._registry.interface_resolve_impl(dep.klass, dep.qualifier_value)
                else:
                    dep_class = dep.klass

                maybe_await = "await " if self._registry.factories[dep_class, dep.qualifier_value].is_async else ""
                dep_hash = FactoryCompiler.get_object_id(dep_class, dep.qualifier_value)
                code += f"    _obj_dep_{name} = {maybe_await}factories[{dep_hash}].factory(container)\n"
            kwargs += f"{name}=_obj_dep_{name}, "

        maybe_await = "await " if factory.factory_type == FactoryType.COROUTINE_FN else ""

        code += f"    instance = {maybe_await}ORIGINAL_FACTORY({kwargs.strip()})\n"

        if factory.factory_type in GENERATOR_FACTORY_TYPES:
            if lifetime == "singleton":
                code += "    container._global_scope_exit_stack.append(instance)\n"
            else:
                code += "    container._current_scope_exit_stack.append(instance)\n"

            if factory.factory_type == FactoryType.GENERATOR:
                code += "    instance = next(instance)\n"
            else:
                code += "    instance = await instance.__anext__()\n"

        if cache_created_instance:
            code += "    storage[OBJ_ID] = instance\n"
            if is_interface:
                code += "    storage[ORIGINAL_OBJ_ID] = instance\n"

        code += "    return instance\n"

        return code, factory.is_async

    def _compile_and_create_function(self, factory: ServiceFactory, impl: type, qualifier: Hashable) -> CompiledFactory:
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
                "ORIGINAL_FACTORY": self._registry.ctors[obj_id][0],
                "TemplatedString": TemplatedString,
                "WireupError": WireupError,
                "_CONTAINER_SCOPE_ERROR_MSG": _CONTAINER_SCOPE_ERROR_MSG,
                "parameters": self._registry.parameters,
            }

            compiled_code = compile(source, f"<{_WIREUP_GENERATED_FACTORY_NAME}_{obj_id}>", "exec")
            exec(compiled_code, namespace)  # noqa: S102

            return CompiledFactory(factory=namespace[_WIREUP_GENERATED_FACTORY_NAME], is_async=is_async)

        except Exception as e:
            msg = f"Failed to compile generated factory {obj_id}: {e}"
            raise WireupError(msg) from e
