from typing import Any

from wireup.errors import UnknownParameterError, WireupError
from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.types import AnnotatedParameter, ParameterWrapper


def assert_dependencies_valid(container: BaseContainer) -> None:
    """Assert that all required dependencies exist for this container instance."""
    for (impl, _), service_factory in container._registry.factories.items():
        for name, dependency in container._registry.dependencies[service_factory.factory].items():
            assert_dependency_exists(container=container, parameter=dependency, target=impl, name=name)

            if (
                not dependency.is_parameter
                and container._registry.lifetime[impl] == "singleton"
                and (dep_lifetime := container._registry.lifetime[dependency.klass]) != "singleton"
            ):
                msg = (
                    f"Parameter '{name}' of {type(impl).__name__.capitalize()} {impl.__module__}.{impl.__name__} "
                    f"depends on a service with a '{dep_lifetime}' lifetime which is not supported. "
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
            f"depends on an unknown service {stringify_type(parameter.klass)} with qualifier {parameter.qualifier_value}."
        )
        raise WireupError(msg)


def stringify_type(target: type) -> str:
    return f"{type(target).__name__.capitalize()} {target.__module__}.{target.__name__}"
