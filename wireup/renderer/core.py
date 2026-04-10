from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wireup.ioc.types import ConfigInjectionRequest, TemplatedString

if TYPE_CHECKING:
    from wireup.ioc.container.base_container import BaseContainer
    from wireup.ioc.registry import InjectableFactory
    from wireup.ioc.types import AnnotatedParameter, ContainerObjectIdentifier, Qualifier
    from wireup.renderer._consumers import ConsumerRecord

_CONFIG_REF_PATTERN = re.compile(r"\${(.*?)}", flags=re.DOTALL)


@dataclass(frozen=True)
class GraphOptions:
    base_module: str | None = None


@dataclass(frozen=True)
class DependencyReference:
    kind: str
    param_name: str
    config_keys: tuple[str, ...] = ()
    service_id: str | None = None
    qualifier: Any = None


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


@dataclass(frozen=True)
class _GraphNodeSpec:
    node_id: str
    label: str
    kind: str
    lifetime: str | None
    group: str
    module: str
    factory_name: str | None


def to_graph_data(container: BaseContainer, *, options: GraphOptions | None = None) -> GraphData:
    opts = options or GraphOptions()
    return _build_graph(container, base_module=opts.base_module)


def _build_graph(
    container: BaseContainer,
    *,
    base_module: str | None,
) -> GraphData:
    service_nodes = _collect_service_nodes(container, base_module=base_module)
    config_nodes: dict[str, _GraphNodeSpec] = {}
    consumer_nodes: dict[str, _GraphNodeSpec] = {}
    edges: set[tuple[str, str, str]] = set()

    _add_service_edges(
        container,
        service_nodes=service_nodes,
        config_nodes=config_nodes,
        edges=edges,
    )
    _add_consumer_edges(
        container,
        service_nodes=service_nodes,
        config_nodes=config_nodes,
        consumer_nodes=consumer_nodes,
        edges=edges,
    )

    return _build_graph_data(
        config_nodes=config_nodes,
        service_nodes=service_nodes,
        consumer_nodes=consumer_nodes,
        edges=edges,
    )


def _collect_service_nodes(
    container: BaseContainer,
    *,
    base_module: str | None,
) -> dict[str, _GraphNodeSpec]:
    registry = container._registry
    service_nodes: dict[str, _GraphNodeSpec] = {}

    for obj_id in sorted(registry.factories, key=_sort_obj_id):
        impl, qualifier = _split_obj_id(obj_id)
        factory = registry.factories[obj_id]
        service_node = _service_node(impl, qualifier, factory, registry.lifetime[obj_id], base_module)
        service_nodes[service_node.node_id] = service_node

    return service_nodes


def _add_service_edges(
    container: BaseContainer,
    *,
    service_nodes: dict[str, _GraphNodeSpec],
    config_nodes: dict[str, _GraphNodeSpec],
    edges: set[tuple[str, str, str]],
) -> None:
    registry = container._registry

    for obj_id in sorted(registry.factories, key=_sort_obj_id):
        impl, qualifier = _split_obj_id(obj_id)
        service_node = service_nodes[_node_id(f"{impl.__module__}.{impl.__qualname__}", qualifier)]
        factory = registry.factories[obj_id]

        _add_dependency_edges(
            resolve_dependencies(container, registry.dependencies[factory.factory]),
            target_node_id=service_node.node_id,
            service_nodes=service_nodes,
            config_nodes=config_nodes,
            edges=edges,
        )


def _add_consumer_edges(
    container: BaseContainer,
    *,
    service_nodes: dict[str, _GraphNodeSpec],
    config_nodes: dict[str, _GraphNodeSpec],
    consumer_nodes: dict[str, _GraphNodeSpec],
    edges: set[tuple[str, str, str]],
) -> None:
    for consumer in sorted(container._consumers.values(), key=lambda item: item.id):
        consumer_node = _consumer_node(consumer)
        consumer_nodes[consumer_node.node_id] = consumer_node

        _add_dependency_edges(
            consumer.dependencies,
            target_node_id=consumer_node.node_id,
            service_nodes=service_nodes,
            config_nodes=config_nodes,
            edges=edges,
        )


def _add_dependency_edges(
    dependencies: tuple[DependencyReference, ...],
    *,
    target_node_id: str,
    service_nodes: dict[str, _GraphNodeSpec],
    config_nodes: dict[str, _GraphNodeSpec],
    edges: set[tuple[str, str, str]],
) -> None:
    for dependency in dependencies:
        if dependency.kind == "config":
            for config_key in dependency.config_keys:
                config_node = _config_node(config_key)
                config_nodes[config_node.node_id] = config_node
                edges.add((config_node.node_id, target_node_id, dependency.param_name))
            continue

        service_node_id = _node_id(dependency.service_id or "", dependency.qualifier)
        if service_node_id in service_nodes:
            edges.add((service_node_id, target_node_id, dependency.param_name))


def _build_graph_data(
    *,
    config_nodes: dict[str, _GraphNodeSpec],
    service_nodes: dict[str, _GraphNodeSpec],
    consumer_nodes: dict[str, _GraphNodeSpec],
    edges: set[tuple[str, str, str]],
) -> GraphData:
    nodes = [*config_nodes.values(), *service_nodes.values(), *consumer_nodes.values()]
    groups: dict[str, GraphGroup] = {}
    node_payload: list[GraphNode] = []
    for node in sorted(nodes, key=lambda item: item.node_id):
        group_id = _group_id(node.group)
        groups[group_id] = GraphGroup(id=group_id, label=node.group, kind="group", module=node.group)
        node_payload.append(
            GraphNode(
                id=node.node_id,
                label=node.label,
                kind=node.kind,
                lifetime=node.lifetime,
                module=node.module,
                parent=group_id,
                original_parent=group_id,
                group=node.group,
                factory_name=node.factory_name,
            )
        )

    edge_payload: list[GraphEdge] = []
    for index, (source, target, label) in enumerate(sorted(edges)):
        edge_payload.append(
            GraphEdge(
                id=f"edge_{index}",
                source=source,
                target=target,
                label=label,
                kind="dependency",
            )
        )

    return GraphData(
        groups=tuple(sorted(groups.values(), key=lambda item: item.id)),
        nodes=tuple(node_payload),
        edges=tuple(edge_payload),
    )


def resolve_dependencies(
    container: BaseContainer,
    names_to_inject: dict[str, AnnotatedParameter],
) -> tuple[DependencyReference, ...]:
    dependencies: list[DependencyReference] = []

    for param_name, parameter in sorted(names_to_inject.items()):
        config_keys = extract_config_sources(
            parameter.annotation,
        )
        if config_keys:
            dependencies.append(
                DependencyReference(
                    kind="config",
                    param_name=param_name,
                    config_keys=config_keys,
                )
            )
            continue

        impl = container._registry.get_implementation(parameter.klass, parameter.qualifier_value)
        dependencies.append(
            DependencyReference(
                kind="service",
                param_name=param_name,
                service_id=f"{impl.__module__}.{impl.__qualname__}",
                qualifier=parameter.qualifier_value,
            )
        )

    return tuple(dependencies)


def _service_node(
    impl: type[Any],
    qualifier: Qualifier | None,
    factory: InjectableFactory,
    lifetime: str,
    base_module: str | None,
) -> _GraphNodeSpec:
    is_factory = not isinstance(factory.factory, type)
    label_prefix = "🏭" if is_factory else "🐍"
    label = f"{label_prefix} {impl.__name__}"
    if qualifier is not None:
        label = f"{label} [{qualifier}]"

    module_name = factory.factory.__module__
    return _GraphNodeSpec(
        node_id=_node_id(f"{impl.__module__}.{impl.__qualname__}", qualifier),
        label=label,
        kind="factory" if is_factory else "service",
        lifetime=lifetime,
        group=_display_module_name(module_name, base_module),
        module=module_name,
        factory_name=None if not is_factory else factory.factory.__name__,
    )


def _config_node(config_key: str) -> _GraphNodeSpec:
    return _GraphNodeSpec(
        node_id=_node_id(f"config.{config_key}", None),
        label=f"⚙️ {config_key}",
        kind="config",
        lifetime=None,
        group="Configuration",
        module="config",
        factory_name=None,
    )


def _consumer_node(consumer: ConsumerRecord) -> _GraphNodeSpec:
    return _GraphNodeSpec(
        node_id=_node_id(f"consumer.{consumer.id}", None),
        label=consumer.label,
        kind="consumer",
        lifetime=None,
        group=consumer.group,
        module=consumer.module,
        factory_name=None,
    )


def extract_config_sources(
    annotation: object,
) -> tuple[str, ...]:
    if not isinstance(annotation, ConfigInjectionRequest):
        return ()

    config_key = annotation.config_key
    if isinstance(config_key, TemplatedString):
        keys = tuple(dict.fromkeys(_CONFIG_REF_PATTERN.findall(config_key.value)))
    else:
        keys = (config_key,)

    keys = tuple(_collapse_config_key(key) for key in keys)
    return tuple(dict.fromkeys(keys))


def _collapse_config_key(key: str) -> str:
    return key if "." not in key else key.split(".", maxsplit=1)[0]


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
