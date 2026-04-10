from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wireup.renderer.core import DependencyReference, resolve_dependencies

if TYPE_CHECKING:
    from wireup.ioc.container.base_container import BaseContainer
    from wireup.ioc.types import AnnotatedParameter


@dataclass(frozen=True)
class ConsumerRecord:
    kind: str
    id: str
    label: str
    group: str
    module: str
    dependencies: tuple[DependencyReference, ...]


def build_consumer_dependencies(
    container: BaseContainer,
    names_to_inject: dict[str, AnnotatedParameter],
) -> tuple[DependencyReference, ...]:
    return resolve_dependencies(container, names_to_inject)


def record_consumer(
    container: BaseContainer,
    *,
    kind: str,
    consumer_id: str,
    label: str,
    group: str,
    module: str,
    names_to_inject: dict[str, AnnotatedParameter],
    extra_dependencies: tuple[DependencyReference, ...] = (),
) -> None:
    container._consumers[consumer_id] = ConsumerRecord(
        kind=kind,
        id=consumer_id,
        label=label,
        group=group,
        module=module,
        dependencies=build_consumer_dependencies(container, names_to_inject) + extra_dependencies,
    )
