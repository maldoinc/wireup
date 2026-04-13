from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wireup.errors import CollectionInterfaceUnknownError, UnknownParameterError, WireupError
from wireup.ioc.type_analysis import analyze_type
from wireup.ioc.types import (
    AnnotatedParameter,
    CollectionInjectionRequest,
    ConfigInjectionRequest,
    get_container_object_id,
)
from wireup.util import format_name, stringify_type

if TYPE_CHECKING:
    from wireup.ioc.registry import ContainerRegistry


def validate_registry(registry: ContainerRegistry) -> None:
    """Assert that all required dependencies exist for this registry instance."""
    for obj_id, injectable_factory in registry.factories.items():
        if isinstance(obj_id, tuple):
            impl, impl_qualifier = obj_id
        else:
            impl, impl_qualifier = obj_id, None
        unknown_dependencies_with_default: list[str] = []

        for name, dependency in registry.dependencies[injectable_factory.factory].items():
            try:
                assert_dependency_exists(
                    parameters=registry.parameters,
                    is_type_with_qualifier_known=registry.is_type_with_qualifier_known,
                    parameter=dependency,
                    target=impl,
                    name=name,
                    registry=registry,
                )
            except WireupError:
                if dependency.has_default_value:
                    unknown_dependencies_with_default.append(name)
                    continue

                raise

            assert_lifetime_valid(
                registry,
                get_container_object_id(impl, impl_qualifier),
                name,
                dependency,
                injectable_factory.factory,
            )
            assert_valid_resolution_path(
                registry=registry,
                dependency=dependency,
                path=[],
            )

        for name in unknown_dependencies_with_default:
            del registry.dependencies[injectable_factory.factory][name]


def assert_lifetime_valid(
    registry: ContainerRegistry,
    object_id: Any,
    parameter_name: str,
    dependency: AnnotatedParameter,
    factory: Any,
) -> None:
    if dependency.is_parameter:
        return

    if isinstance(dependency.annotation, CollectionInjectionRequest):
        if registry.lifetime[object_id] != "singleton":
            return
        for _, impl_obj_id in registry.iter_impls_for_type(dependency.annotation.inner_type):
            impl_lifetime = registry.lifetime[impl_obj_id]
            if impl_lifetime != "singleton":
                msg = (
                    f"Parameter '{parameter_name}' of {stringify_type(factory)} "
                    f"depends on an injectable with a '{impl_lifetime}' lifetime which is not supported. "
                    "Singletons can only depend on other singletons."
                )
                raise WireupError(msg)
        return

    dependency_lifetime = registry.get_lifetime(dependency.klass, dependency.qualifier_value)

    if registry.lifetime[object_id] == "singleton" and dependency_lifetime != "singleton":
        msg = (
            f"Parameter '{parameter_name}' of {stringify_type(factory)} "
            f"depends on an injectable with a '{dependency_lifetime}' lifetime which is not supported. "
            "Singletons can only depend on other singletons."
        )
        raise WireupError(msg)


def assert_dependency_exists(  # noqa: PLR0913
    *,
    parameters: Any,
    is_type_with_qualifier_known: Any,
    parameter: AnnotatedParameter,
    target: Any,
    name: str,
    registry: ContainerRegistry | None = None,
) -> None:
    """Assert that a dependency exists in the container for the given annotated parameter."""
    if isinstance(parameter.annotation, ConfigInjectionRequest):
        try:
            parameters.get(parameter.annotation.config_key)
        except UnknownParameterError as e:
            msg = (
                f"Parameter '{name}' of {stringify_type(target)} "
                f"depends on an unknown Wireup config key '{e.parameter_name}'"
                + (
                    ""
                    if isinstance(parameter.annotation.config_key, str)
                    else f" requested in expression '{parameter.annotation.config_key.value}'"
                )
                + "."
            )
            raise WireupError(msg) from e
        return

    if isinstance(parameter.annotation, CollectionInjectionRequest):
        inner_type = parameter.annotation.inner_type
        if registry is None or (inner_type not in registry.interfaces and inner_type not in registry.impls):
            raise CollectionInterfaceUnknownError(inner_type, name, target)
        return

    if not is_type_with_qualifier_known(parameter.klass, qualifier=parameter.qualifier_value):
        type_str = format_name(analyze_type(parameter.klass).raw_type, parameter.qualifier_value)
        msg = f"Parameter '{name}' of {stringify_type(target)} has an unknown dependency on {type_str}."
        raise WireupError(msg)


def _assert_collection_resolution_path(
    *,
    registry: ContainerRegistry,
    dependency: AnnotatedParameter,
    annotation: CollectionInjectionRequest,
    path: list[tuple[AnnotatedParameter, Any]],
) -> None:
    """Recurse through each impl of a collection dep so cycles passing through it are detected."""
    for _, impl_obj_id in registry.iter_impls_for_type(annotation.inner_type):
        if isinstance(impl_obj_id, tuple):
            impl_klass, impl_qualifier = impl_obj_id
        else:
            impl_klass, impl_qualifier = impl_obj_id, None
        impl_factory = registry.factories[impl_obj_id]
        new_path: list[tuple[AnnotatedParameter, Any]] = [*path, (dependency, impl_factory)]
        if any(p.klass == impl_klass and p.qualifier_value == impl_qualifier for p, _ in path):
            inner_name = format_name(annotation.inner_type, None)
            msg = f"Circular dependency detected through collection dependency {inner_name}"
            raise WireupError(msg)
        for next_dependency in registry.dependencies[impl_factory.factory].values():
            assert_valid_resolution_path(
                registry=registry,
                dependency=next_dependency,
                path=new_path,
            )


def assert_valid_resolution_path(
    *,
    registry: ContainerRegistry,
    dependency: AnnotatedParameter,
    path: list[tuple[AnnotatedParameter, Any]],
) -> None:
    """Assert that the resolution path for a dependency does not create a cycle."""
    if dependency.is_parameter:
        return

    if isinstance(dependency.annotation, CollectionInjectionRequest):
        _assert_collection_resolution_path(
            registry=registry,
            dependency=dependency,
            annotation=dependency.annotation,
            path=path,
        )
        return

    if dependency.klass in registry.interfaces:
        return
    dependency_injectable_factory = registry.factories[
        get_container_object_id(dependency.klass, dependency.qualifier_value)
    ]
    new_path = [*path, (dependency, dependency_injectable_factory)]

    if any(p.klass == dependency.klass and p.qualifier_value == dependency.qualifier_value for p, _ in path):

        def stringify_dependency(p: AnnotatedParameter, factory: Any) -> str:
            descriptors = [
                f"created via {factory.factory.__module__}.{factory.factory.__name__}" if factory else None,
            ]
            qualifier_desc = ", ".join([d for d in descriptors if d is not None])
            qualifier_desc = f" ({qualifier_desc})" if qualifier_desc else ""

            return f"{format_name(p.klass, p.qualifier_value)}{qualifier_desc}"

        cycle_path = "\n -> ".join(f"{stringify_dependency(p, factory)}" for p, factory in new_path)
        msg = f"Circular dependency detected for {cycle_path} ! Cycle here"
        raise WireupError(msg)

    for next_dependency in registry.dependencies[dependency_injectable_factory.factory].values():
        assert_valid_resolution_path(
            registry=registry,
            dependency=next_dependency,
            path=new_path,
        )
