from __future__ import annotations

import inspect
import typing
from typing import Any

from wireup.errors import WireupError
from wireup.ioc.types import AnnotatedParameter, AnyCallable, InjectableType
from wireup.ioc.util import get_globals, param_get_annotation

if typing.TYPE_CHECKING:
    from wireup.ioc.container.base_container import BaseContainer

from wireup.errors import UnknownParameterError
from wireup.ioc.types import ParameterWrapper


def hide_annotated_names(func: AnyCallable) -> None:
    if hasattr(func, "__wireup_names__"):
        return

    names_to_hide = get_inject_annotated_parameters(func)

    if not names_to_hide:
        return

    orig_sig = inspect.signature(func)
    filtered_params = {name: param for name, param in orig_sig.parameters.items() if param.name not in names_to_hide}
    new_sig = inspect.Signature(parameters=list(filtered_params.values()), return_annotation=orig_sig.return_annotation)
    new_annotations = {
        name: annotation for name, annotation in func.__annotations__.items() if name not in names_to_hide
    }

    func.__wireup_names__ = get_inject_annotated_parameters(func)  # type: ignore[attr-defined]
    func.__signature__ = new_sig  # type: ignore[attr-defined]
    func.__annotations__ = new_annotations

    return


def assert_dependencies_valid(container: BaseContainer) -> None:
    """Assert that all required dependencies exist for this container instance."""
    for (impl, _), service_factory in container._registry.factories.items():
        for name, dependency in container._registry.dependencies[service_factory.factory].items():
            assert_dependency_exists(container=container, parameter=dependency, target=impl, name=name)
            assert_lifetime_valid(container, impl, name, dependency, service_factory.factory)


def assert_lifetime_valid(
    container: BaseContainer, impl: Any, parameter_name: str, dependency: AnnotatedParameter, factory: AnyCallable
) -> None:
    if dependency.is_parameter:
        return

    dependency_class = (
        container._registry.interface_resolve_impl(dependency.klass, dependency.qualifier_value)
        if dependency.klass in container._registry.interfaces
        else dependency.klass
    )
    dependency_lifetime = container._registry.lifetime[dependency_class]

    if container._registry.lifetime[impl] == "singleton" and dependency_lifetime != "singleton":
        msg = (
            f"Parameter '{parameter_name}' of {stringify_type(factory)} "
            f"depends on a service with a '{dependency_lifetime}' lifetime which is not supported. "
            "Singletons can only depend on other singletons."
        )
        raise WireupError(msg)


def assert_dependency_exists(container: BaseContainer, parameter: AnnotatedParameter, target: Any, name: str) -> None:
    """Assert that a dependency exists in the container for the given annotated parameter."""
    if isinstance(parameter.annotation, ParameterWrapper):
        try:
            container.params.get(parameter.annotation.param)
        except UnknownParameterError as e:
            msg = (
                f"Parameter '{name}' of {stringify_type(target)} "
                f"depends on an unknown Wireup parameter '{e.parameter_name}'"
                + (
                    ""
                    if isinstance(parameter.annotation.param, str)
                    else f" requested in expression '{parameter.annotation.param.value}'"
                )
                + "."
            )
            raise WireupError(msg) from e
    elif not container._registry.is_type_with_qualifier_known(parameter.klass, qualifier=parameter.qualifier_value):
        msg = (
            f"Parameter '{name}' of {stringify_type(target)} "
            f"depends on an unknown service {stringify_type(parameter.klass)} "
            f"with qualifier {parameter.qualifier_value}."
        )
        raise WireupError(msg)


def stringify_type(target: type | AnyCallable) -> str:
    return f"{type(target).__name__.capitalize()} {target.__module__}.{target.__name__}"


def get_inject_annotated_parameters(target: AnyCallable) -> dict[str, AnnotatedParameter]:
    """Retrieve annotated parameters from a given callable target.

    This function inspects the signature of the provided callable and returns a dictionary
    of parameter names and their corresponding annotated parameters, filtered by those
    that are instances of `InjectableType`.

    Args:
        target (AnyCallable): The callable whose parameters are to be inspected.

    Returns:
        dict[str, AnnotatedParameter]: A dictionary where the keys are parameter names
        and the values are the annotated parameters that are instances of `InjectableType`.

    """
    if hasattr(target, "__wireup_names__"):
        return target.__wireup_names__  # type:ignore[attr-defined]

    return {
        name: param
        for name, parameter in inspect.signature(target).parameters.items()
        if (param := param_get_annotation(parameter, globalns=get_globals(target)))
        and isinstance(param.annotation, InjectableType)
    }


def get_valid_injection_annotated_parameters(
    container: BaseContainer, target: AnyCallable
) -> dict[str, AnnotatedParameter]:
    names_to_inject = get_inject_annotated_parameters(target)

    for name, parameter in names_to_inject.items():
        assert_dependency_exists(container, parameter=parameter, target=target, name=name)

    return names_to_inject
