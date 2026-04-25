from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wireup.renderer._consumers import get_consumers
from wireup.renderer._dependencies import (
    ConfigDependencyReference,
    DependencyReference,
    resolve_dependencies,
)

if TYPE_CHECKING:
    from wireup.ioc.container.base_container import BaseContainer
    from wireup.ioc.registry import InjectableFactory
    from wireup.ioc.types import ContainerObjectIdentifier, Qualifier
    from wireup.renderer._consumers import ConsumerRecord


@dataclass(frozen=True)
class GraphOptions:
    base_module: str | None = None


@dataclass(frozen=True)
class GraphGroup:
    id: str
    label: str
    kind: str
    module: str


@dataclass(frozen=True)
class GraphNode:
    id: str
    label: str
    kind: str
    lifetime: str | None
    module: str
    parent: str
    original_parent: str
    group: str
    factory_name: str | None


@dataclass(frozen=True)
class GraphEdge:
    id: str
    source: str
    target: str
    label: str
    kind: str


@dataclass(frozen=True)
class GraphData:
    groups: tuple[GraphGroup, ...]
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


def to_graph_data(container: BaseContainer, *, options: GraphOptions | None = None) -> GraphData:
    opts = options or GraphOptions()
    service_nodes = _service_nodes(container, base_module=opts.base_module)
    consumer_nodes = _consumer_nodes(container)
    config_nodes: dict[str, GraphNode] = {}
    edge_refs: set[tuple[str, str, str]] = set()

    for node, dependencies in [*service_nodes.values(), *consumer_nodes.values()]:
        _collect_edges(
            dependencies,
            target_node_id=node.id,
            service_nodes=service_nodes,
            config_nodes=config_nodes,
            edge_refs=edge_refs,
        )

    nodes = tuple(
        sorted(
            [
                *config_nodes.values(),
                *(node for node, _ in service_nodes.values()),
                *(node for node, _ in consumer_nodes.values()),
            ],
            key=lambda item: item.id,
        )
    )
    groups = tuple(sorted(_groups_for_nodes(nodes), key=lambda item: item.id))
    edges = tuple(
        GraphEdge(
            id=f"edge_{index}",
            source=source,
            target=target,
            label=label,
            kind="dependency",
        )
        for index, (source, target, label) in enumerate(sorted(edge_refs))
    )
    return GraphData(groups=groups, nodes=nodes, edges=edges)


def _service_nodes(
    container: BaseContainer,
    *,
    base_module: str | None,
) -> dict[str, tuple[GraphNode, tuple[DependencyReference, ...]]]:
    registry = container._registry
    nodes: dict[str, tuple[GraphNode, tuple[DependencyReference, ...]]] = {}

    for obj_id in registry.factories:
        impl, qualifier = _split_obj_id(obj_id)
        factory = registry.factories[obj_id]
        node = _service_node(impl, qualifier, factory, registry.lifetime[obj_id], base_module)
        dependencies = resolve_dependencies(container, registry.dependencies[factory.factory])
        nodes[node.id] = (node, dependencies)

    return nodes


def _consumer_nodes(
    container: BaseContainer,
) -> dict[str, tuple[GraphNode, tuple[DependencyReference, ...]]]:
    nodes: dict[str, tuple[GraphNode, tuple[DependencyReference, ...]]] = {}
    for consumer in get_consumers(container):
        node = _consumer_node(consumer)
        nodes[node.id] = (node, consumer.dependencies)

    return nodes


def _collect_edges(
    dependencies: tuple[DependencyReference, ...],
    *,
    target_node_id: str,
    service_nodes: dict[str, tuple[GraphNode, tuple[DependencyReference, ...]]],
    config_nodes: dict[str, GraphNode],
    edge_refs: set[tuple[str, str, str]],
) -> None:
    for dependency in dependencies:
        if isinstance(dependency, ConfigDependencyReference):
            for config_key in dependency.config_keys:
                config_node = _config_node(config_key)
                config_nodes[config_node.id] = config_node
                edge_refs.add((config_node.id, target_node_id, dependency.param_name))
            continue
        service_node_id = _node_id(dependency.service_id, dependency.qualifier)
        if service_node_id in service_nodes:
            edge_refs.add((service_node_id, target_node_id, dependency.param_name))


def _groups_for_nodes(nodes: tuple[GraphNode, ...]) -> tuple[GraphGroup, ...]:
    groups: dict[str, GraphGroup] = {}
    for node in nodes:
        group_id = _group_id(node.group)
        groups[group_id] = GraphGroup(
            id=group_id,
            label=node.group,
            kind="group",
            module=node.group,
        )
    return tuple(groups.values())


def _service_node(
    impl: type[Any],
    qualifier: Qualifier | None,
    factory: InjectableFactory,
    lifetime: str,
    base_module: str | None,
) -> GraphNode:
    is_factory = not isinstance(factory.factory, type)
    label_prefix = "🏭" if is_factory else "🐍"
    label = f"{label_prefix} {impl.__name__}"
    if qualifier is not None:
        label = f"{label} [{qualifier}]"

    module_name = factory.factory.__module__
    group = _display_module_name(module_name, base_module)
    parent = _group_id(group)
    return GraphNode(
        id=_node_id(f"{impl.__module__}.{impl.__qualname__}", qualifier),
        label=label,
        kind="factory" if is_factory else "service",
        lifetime=lifetime,
        module=module_name,
        parent=parent,
        original_parent=parent,
        group=group,
        factory_name=None if not is_factory else factory.factory.__name__,
    )


def _config_node(config_key: str) -> GraphNode:
    group = "Configuration"
    parent = _group_id(group)
    return GraphNode(
        id=_node_id(f"config.{config_key}", None),
        label=f"⚙️ {config_key}",
        kind="config",
        lifetime=None,
        module="config",
        parent=parent,
        original_parent=parent,
        group=group,
        factory_name=None,
    )


def _consumer_node(consumer: ConsumerRecord) -> GraphNode:
    parent = _group_id(consumer.group)
    return GraphNode(
        id=_node_id(f"consumer.{consumer.id}", None),
        label=consumer.label,
        kind="consumer",
        lifetime=None,
        module=consumer.module,
        parent=parent,
        original_parent=parent,
        group=consumer.group,
        factory_name=None,
    )


def _sort_obj_id(obj_id: ContainerObjectIdentifier) -> tuple[str, str]:
    impl, qualifier = _split_obj_id(obj_id)
    return (f"{impl.__module__}.{impl.__qualname__}", "" if qualifier is None else str(qualifier))


def _split_obj_id(obj_id: ContainerObjectIdentifier) -> tuple[type[Any], Qualifier | None]:
    return obj_id if isinstance(obj_id, tuple) else (obj_id, None)


def _node_id(name: str, qualifier: Qualifier | None) -> str:
    raw = name if qualifier is None else f"{name}.{qualifier}"
    sanitized = re.sub(r"\W+", "_", raw).strip("_")
    if not sanitized:
        return "node"
    if sanitized[0].isdigit():
        return f"n_{sanitized}"
    return sanitized


def _group_id(group_name: str) -> str:
    return f"group_{_node_id(group_name, None)}"


def _display_module_name(module_name: str, base_module: str | None) -> str:
    if not base_module:
        return module_name

    normalized_base = base_module.rstrip(".")
    if module_name == normalized_base:
        return normalized_base.split(".")[-1]

    prefix = f"{normalized_base}."
    if module_name.startswith(prefix):
        return module_name[len(prefix) :]

    return module_name
