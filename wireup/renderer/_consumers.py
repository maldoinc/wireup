from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from weakref import WeakKeyDictionary

from wireup.renderer._dependencies import DependencyReference, resolve_dependencies

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


@dataclass(frozen=True)
class ConsumerMetadata:
    consumer_id: str | None = None
    label: str | None = None
    kind: str = "function"
    group: str | None = None
    module: str | None = None
    extra_dependencies: tuple[DependencyReference, ...] = ()


_CONSUMERS_BY_CONTAINER: WeakKeyDictionary[BaseContainer, dict[str, ConsumerRecord]] = WeakKeyDictionary()


def record_consumer(  # noqa: PLR0913
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
    _CONSUMERS_BY_CONTAINER.setdefault(container, {})[consumer_id] = ConsumerRecord(
        kind=kind,
        id=consumer_id,
        label=label,
        group=group,
        module=module,
        dependencies=resolve_dependencies(container, names_to_inject) + extra_dependencies,
    )


def get_consumers(container: BaseContainer) -> tuple[ConsumerRecord, ...]:
    return tuple(_CONSUMERS_BY_CONTAINER.get(container, {}).values())


def infer_consumer_metadata(target: Any) -> ConsumerMetadata:
    module = getattr(target, "__module__", "unknown")
    qualname = getattr(target, "__qualname__", getattr(target, "__name__", repr(target)))
    consumer_id = f"{module}.{qualname}"

    return ConsumerMetadata(
        consumer_id=consumer_id,
        label=f"ƒ {qualname}",
        group=module,
        module=module,
    )


def record_injected_consumer(
    container: BaseContainer,
    *,
    target: Any,
    names_to_inject: dict[str, AnnotatedParameter],
    metadata: ConsumerMetadata | None = None,
) -> None:
    inferred = infer_consumer_metadata(target)
    provided = metadata or ConsumerMetadata()

    record_consumer(
        container,
        kind=provided.kind,
        consumer_id=provided.consumer_id or inferred.consumer_id or repr(target),
        label=provided.label or inferred.label or repr(target),
        group=provided.group or inferred.group or "Functions",
        module=provided.module or inferred.module or "unknown",
        names_to_inject=names_to_inject,
        extra_dependencies=provided.extra_dependencies,
    )
