from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, Callable

from wireup.codegen import Codegen
from wireup.ioc.container.async_container import BareAsyncContainer, async_container_force_sync_scope
from wireup.ioc.factory_compiler import FactoryCompiler
from wireup.ioc.types import AnnotatedParameter, ConfigInjectionRequest

if TYPE_CHECKING:
    from wireup.ioc.container.base_container import BaseContainer


from wireup.ioc.types import (
    ASYNC_CALLABLE_TYPES,
    GENERATOR_CALLABLE_TYPES,
    CallableType,
)
from wireup.ioc.util import get_callable_type


def compile_injection_wrapper(
    target: Callable[..., Any],
    names_to_inject: dict[str, AnnotatedParameter],
    container: BaseContainer | None,
    scoped_container_supplier: Callable[[], Any] | None,
    middleware: Callable[..., Any] | None,
) -> Callable[..., Any]:
    """Compile a specialized wrapper function for injecting dependencies."""
    func_name = "_wireup_generated_wrapper"
    target_type = get_callable_type(target)
    target_is_async = target_type in ASYNC_CALLABLE_TYPES

    namespace: dict[str, Any] = {
        "_wireup_target": target,
        "_wireup_container": container,
        "_wireup_scoped_container_supplier": scoped_container_supplier,
        "_wireup_middleware": middleware,
        "_wireup_async_container_force_sync_scope": async_container_force_sync_scope,
    }

    gen = Codegen()
    gen += f"{'async ' if target_is_async else ''}def {func_name}(*args, **kwargs):"
    with gen.indent():
        generate_injection_body(
            gen,
            names_to_inject,
            container,
            scoped_container_supplier,
            middleware,
            target_type,
            namespace,
            is_async=target_is_async,
        )

    code = gen.get_source()
    exec(code, namespace)  # noqa: S102
    wrapper = namespace[func_name]
    wrapper.__wireup_generated_code__ = code
    return functools.wraps(target)(wrapper)


def generate_injection_body(  # noqa: PLR0913
    gen: Codegen,
    names_to_inject: dict[str, AnnotatedParameter],
    container: BaseContainer | None,
    scoped_container_supplier: Callable[[], Any] | None,
    middleware: Callable[..., Any] | None,
    target_type: CallableType,
    namespace: dict[str, Any],
    *,
    is_async: bool,
) -> None:
    if scoped_container_supplier:
        gen += "scope = _wireup_scoped_container_supplier()"
        _generate_middleware_and_injection(
            gen,
            names_to_inject,
            target_type,
            container,
            middleware,
            namespace,
        )
        return
    if not container:
        msg = "Container or scoped_container_supplier must be provided for injection."
        raise ValueError(msg)

    if _injection_requires_scope(names_to_inject, container, middleware):
        if isinstance(container, BareAsyncContainer) and not is_async:
            scope_manager = "_wireup_async_container_force_sync_scope(_wireup_container)"
        else:
            scope_manager = "_wireup_container.enter_scope()"

        gen += f"{'async ' if is_async else ''}with {scope_manager} as scope:"
        with gen.indent():
            _generate_middleware_and_injection(
                gen,
                names_to_inject,
                target_type,
                container,
                middleware,
                namespace,
            )
        return

    namespace["scope"] = container
    _generate_middleware_and_injection(
        gen,
        names_to_inject,
        target_type,
        container,
        middleware,
        namespace,
    )


def _injection_requires_scope(
    names_to_inject: dict[str, AnnotatedParameter], container: BaseContainer, middleware: Callable[..., Any] | None
) -> bool:
    # Middlewares require a scope as the exposed middleware expects a scoped container.
    if middleware:
        return True

    for param in names_to_inject.values():
        if isinstance(param.annotation, ConfigInjectionRequest):
            continue

        if container._registry.get_lifetime(param.klass, param.qualifier_value) != "singleton":
            return True

    return False


def _generate_middleware_and_injection(  # noqa: PLR0913
    gen: Codegen,
    names_to_inject: dict[str, AnnotatedParameter],
    target_type: CallableType,
    container: BaseContainer | None,
    middleware: Callable[..., Any] | None,
    namespace: dict[str, Any],
) -> None:
    if middleware:
        gen += "gen_middleware = _wireup_middleware(scope, args, kwargs)"
        gen += "try:"
        with gen.indent():
            gen += "next(gen_middleware)"
            _generate_injection(gen, names_to_inject, target_type, container, namespace)
        gen += "finally:"
        with gen.indent():
            gen += "gen_middleware.close()"
    else:
        _generate_injection(gen, names_to_inject, target_type, container, namespace)


def _generate_injection(  # noqa: C901, PLR0912
    gen: Codegen,
    names_to_inject: dict[str, AnnotatedParameter],
    target_type: CallableType,
    container: BaseContainer | None,
    namespace: dict[str, Any],
) -> None:
    if container:
        namespace["_wireup_singleton_factories"] = container._factories
        namespace["_wireup_scoped_factories"] = container._scoped_compiler.factories

    is_target_async = target_type in ASYNC_CALLABLE_TYPES
    for name, param in names_to_inject.items():
        if not param.annotation:
            continue

        if isinstance(param.annotation, ConfigInjectionRequest):
            # If we have a container instance, inline the config value at compile time
            if container:
                ns_config_val = f"_wireup_config_val_{name}"
                namespace[ns_config_val] = container.config.get(param.annotation.config_key)
                gen += f"kwargs['{name}'] = {ns_config_val}"
            else:
                namespace[f"_wireup_config_key_{name}"] = param.annotation.config_key
                gen += f"kwargs['{name}'] = scope.config.get(_wireup_config_key_{name})"
        else:
            ns_klass_var = f"_wireup_obj_{name}_klass"
            namespace[ns_klass_var] = param.klass
            ns_qualifier_var = f"_wireup_obj_{name}_qualifier"
            namespace[ns_qualifier_var] = param.qualifier_value

            args_str = f"{ns_klass_var}, {ns_qualifier_var}" if param.qualifier_value else ns_klass_var

            # If we have a container instance, we can use that to skip the scope.get call entirely
            # and just call the underlying factories directly.
            if container:
                lifetime = container._registry.get_lifetime(param.klass, param.qualifier_value)
                factories_var = "_wireup_singleton_factories" if lifetime == "singleton" else "_wireup_scoped_factories"
                dependency_obj_id = FactoryCompiler.get_object_id(param.klass, param.qualifier_value)

                # Apply only if:
                #   Async container injecting into an async function
                #   Sync container into a sync function.
                # Avoid async container into sync function
                # In this case the container.get call does a bunch of extra work on the unhappy path
                # to inject cached or overridden instances. Let's skip this path
                if (compiled := namespace[factories_var].get(dependency_obj_id)) and (
                    compiled.is_async == is_target_async or (is_target_async and not compiled.is_async)
                ):
                    maybe_await = "await " if compiled.is_async else ""
                    gen += f"kwargs['{name}'] = {maybe_await}{factories_var}[{dependency_obj_id}].factory(scope)"

                    continue

            if is_target_async:
                gen += f"kwargs['{name}'] = await scope.get({args_str})"
            else:
                gen += f"kwargs['{name}'] = scope._synchronous_get({args_str})"

    if target_type == CallableType.ASYNC_GENERATOR:
        gen += "async for item in _wireup_target(*args, **kwargs):"
        with gen.indent():
            gen += "yield item"
    elif target_type in GENERATOR_CALLABLE_TYPES:
        gen += "yield from _wireup_target(*args, **kwargs)"
    else:
        gen += f"return {'await ' if is_target_async else ''}_wireup_target(*args, **kwargs)"
