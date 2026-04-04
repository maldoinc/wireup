from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from typing_extensions import TypeAlias

from wireup.ioc.types import ConfigInjectionRequest, TemplatedString

if TYPE_CHECKING:
    from wireup.ioc.container.base_container import BaseContainer
    from wireup.ioc.types import AnnotatedParameter

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
        config_keys = extract_config_sources(parameter.annotation)
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


def extract_config_sources(annotation: object) -> tuple[str, ...]:
    if not isinstance(annotation, ConfigInjectionRequest):
        return ()

    config_key = annotation.config_key
    if isinstance(config_key, TemplatedString):
        keys = set(_CONFIG_REF_PATTERN.findall(config_key.value))
    else:
        keys = {config_key}

    return tuple({_collapse_config_key(key) for key in keys})


def _collapse_config_key(key: str) -> str:
    return key if "." not in key else key.split(".", maxsplit=1)[0]
