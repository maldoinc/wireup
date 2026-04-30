from __future__ import annotations

import wireup
import wireup.integration.fastapi as wireup_fastapi
from fastapi import FastAPI
from pet_store_demo_app import factories, fastapi_services, services
from typing_extensions import Annotated
from wireup import Inject, injectable
from wireup._decorators import inject_from_container
from wireup.integration.fastapi import setup
from wireup.renderer._consumers import ConsumerMetadata
from wireup.renderer._dependencies import ServiceDependencyReference
from wireup.renderer.core import GraphOptions, to_graph_data


@injectable(qualifier="primary")
class QualifiedSearchBackend:
    pass


@injectable
class QualifiedSearchService:
    def __init__(self, backend: Annotated[QualifiedSearchBackend, Inject(qualifier="primary")]) -> None:
        self.backend = backend


@injectable
class ConfigDrivenService:
    def __init__(
        self,
        settings: Annotated[str, Inject(expr="${infra.database.url}-${infra.database.schema}-${env.name}")],
    ) -> None:
        self.settings = settings


@injectable
class AuditBackend:
    pass


@injectable
class HandlerService:
    pass


def _create_graph_data():
    app = FastAPI()

    @app.get("/db-session")
    async def db_session(service: wireup.Injected[services.SQLAlchemySession]) -> dict[str, str]:
        return service.describe()

    @app.get("/pets")
    async def list_pets(service: wireup.Injected[services.PetCatalogService]) -> dict[str, object]:
        return service.list_pets()

    @app.get("/whoami")
    async def whoami(service: wireup.Injected[fastapi_services.AuthService]) -> dict[str, str]:
        return service.describe()

    container = wireup.create_async_container(
        injectables=[factories, services, fastapi_services, wireup_fastapi],
        config={
            "auth": {"demo_actor": "shelter-manager"},
            "env": {"name": "demo"},
            "infra": {
                "redis": {"url": "redis://localhost:6379/0"},
                "metrics": {"endpoint": "http://metrics.internal"},
                "database": {
                    "url": "postgresql+psycopg://petstore:petstore@localhost:5432/petstore",
                    "schema": "adoption",
                },
            },
            "services": {"search": {"base_url": "https://search.petstore.example"}},
            "pets": {"store_name": "Happy Tails Shelter", "default_species": "cat"},
            "messaging": {"events": {"topic_prefix": "petstore-events"}},
        },
    )

    setup(container, app)
    return to_graph_data(container, options=GraphOptions(base_module="pet_store_demo_app"))


def test_to_graph_data_returns_expected_groups_nodes_and_edges() -> None:
    graph = _create_graph_data()

    group_ids = {group.id for group in graph.groups}
    assert group_ids >= {
        "group_Configuration",
        "group_FastAPI",
        "group_factories",
        "group_services_adoption",
        "group_services_audit",
        "group_services_infra",
        "group_services_owners",
        "group_services_pets",
        "group_services_session",
    }

    nodes_by_id = {node.id: node for node in graph.nodes}
    assert nodes_by_id["consumer_GET_pets"].label == "🌐 GET /pets"
    assert nodes_by_id["consumer_GET_db_session"].label == "🌐 GET /db-session"
    assert nodes_by_id["consumer_GET_whoami"].label == "🌐 GET /whoami"
    assert nodes_by_id["pet_store_demo_app_factories_SearchClient"].factory_name == "make_search_client"
    assert (
        nodes_by_id["pet_store_demo_app_services_pets_PetCatalogService"].module
        == "pet_store_demo_app.services.pets"
    )
    assert nodes_by_id["pet_store_demo_app_fastapi_services_AuthService"].lifetime == "scoped"
    assert nodes_by_id["pet_store_demo_app_services_adoption_AdoptionService"].group == "services.adoption"
    assert nodes_by_id["pet_store_demo_app_services_owners_OwnerService"].group == "services.owners"
    assert nodes_by_id["pet_store_demo_app_services_session_SQLAlchemySession"].lifetime == "scoped"

    edges = {(edge.source, edge.target, edge.label) for edge in graph.edges}
    assert ("config_services", "pet_store_demo_app_factories_SearchClient", "search_url") in edges
    assert (
        "pet_store_demo_app_factories_SearchClient",
        "pet_store_demo_app_services_pets_PetCatalogService",
        "search",
    ) in edges
    assert (
        "pet_store_demo_app_services_pets_PetCatalogService",
        "pet_store_demo_app_services_adoption_AdoptionService",
        "catalog",
    ) in edges
    assert (
        "pet_store_demo_app_services_infra_ShelterStore",
        "pet_store_demo_app_services_audit_AuditService",
        "shelter_store",
    ) in edges
    assert (
        "pet_store_demo_app_services_pets_PetCatalogService",
        "consumer_GET_pets",
        "service",
    ) in edges
    assert (
        "pet_store_demo_app_services_session_SQLAlchemySession",
        "consumer_GET_db_session",
        "service",
    ) in edges
    assert (
        "pet_store_demo_app_fastapi_services_AuthService",
        "consumer_GET_whoami",
        "service",
    ) in edges


def test_to_graph_data_includes_qualified_service_nodes() -> None:
    container = wireup.create_sync_container(injectables=[QualifiedSearchBackend, QualifiedSearchService])

    graph = to_graph_data(container)

    nodes_by_id = {node.id: node for node in graph.nodes}
    assert "test_unit_test_renderer_core_QualifiedSearchBackend_primary" in nodes_by_id
    assert (
        nodes_by_id["test_unit_test_renderer_core_QualifiedSearchBackend_primary"].label
        == "🐍 QualifiedSearchBackend [primary]"
    )
    assert (
        "test_unit_test_renderer_core_QualifiedSearchBackend_primary",
        "test_unit_test_renderer_core_QualifiedSearchService",
        "backend",
    ) in {(edge.source, edge.target, edge.label) for edge in graph.edges}


def test_to_graph_data_collapses_config_dependencies_to_root_keys() -> None:
    container = wireup.create_sync_container(
        injectables=[ConfigDrivenService],
        config={
            "env": {"name": "demo"},
            "infra": {"database": {"url": "postgresql://demo", "schema": "public"}},
        },
    )

    graph = to_graph_data(container)

    nodes_by_id = {node.id: node for node in graph.nodes}
    assert "config_infra" in nodes_by_id
    assert "config_env" in nodes_by_id
    assert "config_infra_database" not in nodes_by_id

    service_node_id = "test_unit_test_renderer_core_ConfigDrivenService"
    edge_refs = {(edge.source, edge.target, edge.label) for edge in graph.edges}
    assert ("config_infra", service_node_id, "settings") in edge_refs
    assert ("config_env", service_node_id, "settings") in edge_refs
    assert len([edge for edge in graph.edges if edge.target == service_node_id]) == 2


def test_to_graph_data_uses_custom_consumer_metadata_and_extra_dependencies() -> None:
    container = wireup.create_sync_container(injectables=[AuditBackend, HandlerService])

    @inject_from_container(
        container,
        consumer_metadata=ConsumerMetadata(
            consumer_id="custom.route",
            label="🌐 GET /custom",
            kind="fastapi_route",
            group="FastAPI",
            module="tests.handlers",
            extra_dependencies=(
                ServiceDependencyReference(
                    param_name="audit_backend",
                    service_id=f"{AuditBackend.__module__}.{AuditBackend.__qualname__}",
                    qualifier=None,
                ),
            ),
        ),
    )
    def handler(service: wireup.Injected[HandlerService]) -> None:
        assert service is not None

    handler()

    graph = to_graph_data(container)

    nodes_by_id = {node.id: node for node in graph.nodes}
    assert nodes_by_id["consumer_custom_route"].label == "🌐 GET /custom"
    assert nodes_by_id["consumer_custom_route"].group == "FastAPI"
    assert nodes_by_id["consumer_custom_route"].module == "tests.handlers"

    edge_refs = {(edge.source, edge.target, edge.label) for edge in graph.edges}
    assert ("test_unit_test_renderer_core_HandlerService", "consumer_custom_route", "service") in edge_refs
    assert ("test_unit_test_renderer_core_AuditBackend", "consumer_custom_route", "audit_backend") in edge_refs
