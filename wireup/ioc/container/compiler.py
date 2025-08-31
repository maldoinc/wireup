from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Hashable

from wireup.errors import WireupError
from wireup.ioc.service_registry import GENERATOR_FACTORY_TYPES, FactoryType, ServiceRegistry
from wireup.ioc.types import ParameterWrapper, TemplatedString

if TYPE_CHECKING:
    from wireup.ioc.container.base_container import BaseContainer
    from wireup.ioc.parameter import ParameterBag
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


class FactoryCompiler:
    """Compiles factory functions for dependency injection."""

    def __init__(self, registry: ServiceRegistry, params: ParameterBag, *, is_scoped_container: bool) -> None:
        self.registry = registry
        self.params = params
        self.factories: dict[Hashable, CompiledFactory] = {}
        self.named_factories: dict[str, CompiledFactory] = {}
        self.is_scoped_container = is_scoped_container

    @classmethod
    def get_object_id(cls, impl: type, qualifier: Hashable) -> Hashable:
        return impl if qualifier is None else (impl, qualifier)

    def compile(self) -> None:
        self.registry.update_factories_async_flag()

        for impl, qualifiers in self.registry.impls.items():
            for qualifier in qualifiers:
                obj_id = FactoryCompiler.get_object_id(impl, qualifier)

                self.factories[obj_id] = self._compile_and_create_function(
                    self.registry.factories[impl, qualifier],
                    impl,
                    qualifier,
                )
                setattr(self, self.get_fn_name(impl, qualifier), self.factories[obj_id])

        for interface, impls in self.registry.interfaces.items():
            for qualifier, impl in impls.items():
                obj_id = FactoryCompiler.get_object_id(interface, qualifier)

                self.factories[obj_id] = self._compile_and_create_function(
                    self.registry.factories[impl, qualifier],
                    interface,
                    qualifier,
                )
                setattr(self, self.get_fn_name(interface, qualifier), self.factories[obj_id])

    def get_fn_name(self, impl: type, qualifier: Hashable) -> str:
        sanitized_impl = impl.__module__.replace(".", "_") + "_" + impl.__name__.replace(".", "_")
        return f"get_{sanitized_impl}_{qualifier}"

    def _get_factory_code(self, factory: ServiceFactory, impl: type, qualifier: Hashable) -> tuple[str, bool]:  # noqa: C901, PLR0912, PLR0915
        is_interface = self.registry.is_interface_known(impl)
        if is_interface:
            lifetime = self.registry.lifetime[self.registry.interface_resolve_impl(impl, qualifier)]
        else:
            lifetime = self.registry.lifetime[impl]

        generated_function_name = self.get_fn_name(impl, qualifier)

        if lifetime != "singleton" and not self.is_scoped_container:
            code = f"def {generated_function_name}(container):\n"
            code += "    raise WireupError(_CONTAINER_SCOPE_ERROR_MSG)\n"

            return code, False

        maybe_async = "async " if factory.is_async else ""
        code = f"{maybe_async}def {generated_function_name}(container):\n"

        if is_interface:
            code += "    obj_id = RESOLVED_OBJ_ID\n"
        else:
            code += "    obj_id = CURRENT_OBJ_ID\n"

        if lifetime == "singleton":
            code += "    global_object_storage = container._global_scope.objects\n"
            code += "    if res := global_object_storage.get(obj_id):\n"
            code += "        return res\n"
        else:
            code += "    scope_objects = container._current_scope_objects\n"
            code += "    if res := scope_objects.get(obj_id):\n"
            code += "        return res\n"

        kwargs = ""
        for name, dep in self.registry.dependencies[factory.factory].items():
            if isinstance(dep.annotation, ParameterWrapper):
                param_value = (
                    str(dep.annotation.param)
                    if isinstance(dep.annotation.param, TemplatedString)
                    else f'"{dep.annotation.param}"'
                )
                code += f"    _obj_dep_{name} = container.params.get({param_value})\n"
            else:
                if self.registry.is_interface_known(dep.klass):
                    dep_class = self.registry.interface_resolve_impl(dep.klass, dep.qualifier_value)
                else:
                    dep_class = dep.klass

                maybe_await = "await " if self.registry.factories[dep_class, dep.qualifier_value].is_async else ""
                code += f"    _obj_dep_{name} = {maybe_await}self.{self.get_fn_name(dep_class, dep.qualifier_value)}.factory(container)\n"  # noqa: E501
            kwargs += f"{name} = _obj_dep_{name}, "

        maybe_await = "await " if factory.factory_type == FactoryType.COROUTINE_FN else ""

        code += f"    instance = {maybe_await}ORIGINAL_FACTORY({kwargs.strip()})\n"

        if factory.factory_type in GENERATOR_FACTORY_TYPES:
            if lifetime == "singleton":
                code += "    container._global_scope.exit_stack.append(instance)\n"
            else:
                code += "    container._current_scope_exit_stack.append(instance)\n"

            if factory.factory_type == FactoryType.GENERATOR:
                code += "    instance = next(instance)\n"
            else:
                code += "    instance = await instance.__anext__()\n"

        if lifetime == "singleton":
            code += "    global_object_storage[CURRENT_OBJ_ID] = instance\n"
            if is_interface:
                code += "    global_object_storage[obj_id] = instance\n"
        elif lifetime == "scoped":
            code += "    scope_objects[CURRENT_OBJ_ID] = instance\n"
            if is_interface:
                code += "    scope_objects[obj_id] = instance\n"

        code += "    return instance\n"

        print(code)

        return code, factory.is_async

    def _compile_and_create_function(self, factory: ServiceFactory, impl: type, qualifier: Hashable) -> CompiledFactory:
        obj_id = impl, qualifier
        resolved_obj_id = (
            (self.registry.interface_resolve_impl(impl, qualifier), qualifier)
            if self.registry.is_interface_known(impl)
            else None
        )

        source, is_async = self._get_factory_code(factory, impl, qualifier)

        try:
            # Create a namespace with necessary references
            namespace: dict[str, Any] = {
                "self": self,
                "CURRENT_OBJ_ID": obj_id,
                "RESOLVED_OBJ_ID": resolved_obj_id,
                "ORIGINAL_FACTORY": self.registry.ctors[obj_id][0],
                "TemplatedString": TemplatedString,
                "WireupError": WireupError,
                "_CONTAINER_SCOPE_ERROR_MSG": _CONTAINER_SCOPE_ERROR_MSG,
            }

            compiled_code = compile(source, f"<generated_{obj_id}>", "exec")
            exec(compiled_code, namespace)  # noqa: S102

            return CompiledFactory(factory=namespace[self.get_fn_name(impl, qualifier)], is_async=is_async)

        except Exception as e:
            msg = f"Failed to compile generated factory {obj_id}: {e}"
            raise WireupError(msg) from e
