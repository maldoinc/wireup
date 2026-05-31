import re
from dataclasses import dataclass
from typing import Any, TypeAlias

from wireup.ioc.container.base_container import BaseContainer
from wireup.ioc.types import AnnotatedParameter, ConfigInjectionRequest, TemplatedString

_CONFIG_REF_PATTERN = re.compile(r"\${(.*?)}", flags=re.DOTALL)


@dataclass(frozen=True)
class ConfigDependencyReference:
    param_name: str
    config_keys: tuple[str, ...]


@dataclass(frozen=True)
class ServiceDependencyReference:
    param_name: str
    service_id: str
    qualifier: Any = None


DependencyReference: TypeAlias = ConfigDependencyReference | ServiceDependencyReference


def resolve_dependencies(
    container: BaseContainer,
    names_to_inject: dict[str, AnnotatedParameter],
) -> tuple[DependencyReference, ...]:
    dependencies: list[DependencyReference] = []

    for param_name, parameter in names_to_inject.items():
        if isinstance(parameter.annotation, ConfigInjectionRequest):
            config_keys = _get_config_sources(parameter.annotation.config_key)
            if config_keys:
                dependencies.append(
                    ConfigDependencyReference(
                        param_name=param_name,
                        config_keys=config_keys,
                    )
                )
                continue

        impl = container._registry.get_implementation(parameter.klass, parameter.qualifier_value)
        dependencies.append(
            ServiceDependencyReference(
                param_name=param_name,
                service_id=f"{impl.__module__}.{impl.__qualname__}",
                qualifier=parameter.qualifier_value,
            )
        )

    return tuple(dependencies)


def _get_config_sources(config_key: str | TemplatedString) -> tuple[str, ...]:
    if isinstance(config_key, TemplatedString):
        keys = set(_CONFIG_REF_PATTERN.findall(config_key.value))
    else:
        keys = {config_key}

    return tuple({_get_config_key_root_name(key) for key in keys})


def _get_config_key_root_name(key: str) -> str:
    return key.split(".", maxsplit=1)[0]
