from __future__ import annotations

import wireup
import wireup.integration.fastapi as wireup_fastapi
from fastapi import FastAPI
from graph_demo_app import factories, services
from graph_demo_app.services.session import RequestContextService
from graph_demo_app.services.weather import WeatherService
from wireup.integration.fastapi import setup
from wireup.renderer.core import GraphData, GraphEdge, GraphGroup, GraphNode, GraphOptions, to_graph_data


def _create_graph_data() -> GraphData:
    app = FastAPI()

    @app.get("/request-context")
    async def request_context(service: wireup.Injected[RequestContextService]) -> dict[str, str]:
        return service.snapshot()

    @app.get("/weather")
    async def weather(service: wireup.Injected[WeatherService]) -> dict[str, str]:
        return service.snapshot()

    container = wireup.create_async_container(
        injectables=[factories, services, wireup_fastapi],
        config={
            "env": {"name": "demo"},
            "infra": {
                "redis": {"url": "redis://localhost:6379/0"},
                "metrics": {"endpoint": "http://metrics.internal"},
            },
            "services": {
                "weather": {
                    "base_url": "https://weather.example",
                    "api_key": "demo-key",
                    "cache_suffix": "forecast",
                }
            },
            "messaging": {"kafka": {"topic_prefix": "weather-audit"}},
        },
    )

    setup(container, app)
    return to_graph_data(container, options=GraphOptions(base_module="graph_demo_app"))


def test_to_graph_data_returns_typed_graph_payload() -> None:
    graph = _create_graph_data()

    assert graph == GraphData(
        groups=(
            GraphGroup(id="group_Configuration", label="Configuration", kind="group", module="Configuration"),
            GraphGroup(id="group_FastAPI", label="FastAPI", kind="group", module="FastAPI"),
            GraphGroup(id="group_factories", label="factories", kind="group", module="factories"),
            GraphGroup(id="group_services_audit", label="services.audit", kind="group", module="services.audit"),
            GraphGroup(id="group_services_kv", label="services.kv", kind="group", module="services.kv"),
            GraphGroup(id="group_services_session", label="services.session", kind="group", module="services.session"),
            GraphGroup(id="group_services_weather", label="services.weather", kind="group", module="services.weather"),
            GraphGroup(
                id="group_wireup_integration_starlette",
                label="wireup.integration.starlette",
                kind="group",
                module="wireup.integration.starlette",
            ),
        ),
        nodes=(
            GraphNode(
                id="config_env",
                label="⚙️ env",
                kind="config",
                lifetime=None,
                module="config",
                parent="group_Configuration",
                original_parent="group_Configuration",
                group="Configuration",
                factory_name=None,
            ),
            GraphNode(
                id="config_infra",
                label="⚙️ infra",
                kind="config",
                lifetime=None,
                module="config",
                parent="group_Configuration",
                original_parent="group_Configuration",
                group="Configuration",
                factory_name=None,
            ),
            GraphNode(
                id="config_messaging",
                label="⚙️ messaging",
                kind="config",
                lifetime=None,
                module="config",
                parent="group_Configuration",
                original_parent="group_Configuration",
                group="Configuration",
                factory_name=None,
            ),
            GraphNode(
                id="config_services",
                label="⚙️ services",
                kind="config",
                lifetime=None,
                module="config",
                parent="group_Configuration",
                original_parent="group_Configuration",
                group="Configuration",
                factory_name=None,
            ),
            GraphNode(
                id="consumer_GET_request_context",
                label="🌐 GET /request-context",
                kind="consumer",
                lifetime=None,
                module="test.unit.test_renderer_core",
                parent="group_FastAPI",
                original_parent="group_FastAPI",
                group="FastAPI",
                factory_name=None,
            ),
            GraphNode(
                id="consumer_GET_weather",
                label="🌐 GET /weather",
                kind="consumer",
                lifetime=None,
                module="test.unit.test_renderer_core",
                parent="group_FastAPI",
                original_parent="group_FastAPI",
                group="FastAPI",
                factory_name=None,
            ),
            GraphNode(
                id="graph_demo_app_factories_HttpClient",
                label="🏭 HttpClient",
                kind="factory",
                lifetime="singleton",
                module="graph_demo_app.factories",
                parent="group_factories",
                original_parent="group_factories",
                group="factories",
                factory_name="make_http_client",
            ),
            GraphNode(
                id="graph_demo_app_services_audit_AuditService",
                label="🐍 AuditService",
                kind="service",
                lifetime="singleton",
                module="graph_demo_app.services.audit",
                parent="group_services_audit",
                original_parent="group_services_audit",
                group="services.audit",
                factory_name=None,
            ),
            GraphNode(
                id="graph_demo_app_services_kv_KeyValueStore",
                label="🐍 KeyValueStore",
                kind="service",
                lifetime="singleton",
                module="graph_demo_app.services.kv",
                parent="group_services_kv",
                original_parent="group_services_kv",
                group="services.kv",
                factory_name=None,
            ),
            GraphNode(
                id="graph_demo_app_services_kv_MetricsClient",
                label="🐍 MetricsClient",
                kind="service",
                lifetime="singleton",
                module="graph_demo_app.services.kv",
                parent="group_services_kv",
                original_parent="group_services_kv",
                group="services.kv",
                factory_name=None,
            ),
            GraphNode(
                id="graph_demo_app_services_kv_RedisConnection",
                label="🐍 RedisConnection",
                kind="service",
                lifetime="singleton",
                module="graph_demo_app.services.kv",
                parent="group_services_kv",
                original_parent="group_services_kv",
                group="services.kv",
                factory_name=None,
            ),
            GraphNode(
                id="graph_demo_app_services_session_RequestContextService",
                label="🐍 RequestContextService",
                kind="service",
                lifetime="scoped",
                module="graph_demo_app.services.session",
                parent="group_services_session",
                original_parent="group_services_session",
                group="services.session",
                factory_name=None,
            ),
            GraphNode(
                id="graph_demo_app_services_session_RequestNonce",
                label="🐍 RequestNonce",
                kind="service",
                lifetime="transient",
                module="graph_demo_app.services.session",
                parent="group_services_session",
                original_parent="group_services_session",
                group="services.session",
                factory_name=None,
            ),
            GraphNode(
                id="graph_demo_app_services_weather_WeatherService",
                label="🐍 WeatherService",
                kind="service",
                lifetime="singleton",
                module="graph_demo_app.services.weather",
                parent="group_services_weather",
                original_parent="group_services_weather",
                group="services.weather",
                factory_name=None,
            ),
            GraphNode(
                id="starlette_requests_Request",
                label="🏭 Request",
                kind="factory",
                lifetime="scoped",
                module="wireup.integration.starlette",
                parent="group_wireup_integration_starlette",
                original_parent="group_wireup_integration_starlette",
                group="wireup.integration.starlette",
                factory_name="request_factory",
            ),
            GraphNode(
                id="starlette_websockets_WebSocket",
                label="🏭 WebSocket",
                kind="factory",
                lifetime="scoped",
                module="wireup.integration.starlette",
                parent="group_wireup_integration_starlette",
                original_parent="group_wireup_integration_starlette",
                group="wireup.integration.starlette",
                factory_name="websocket_factory",
            ),
            GraphNode(
                id="wireup_integration_starlette_WireupTask",
                label="🏭 WireupTask",
                kind="factory",
                lifetime="singleton",
                module="wireup.integration.starlette",
                parent="group_wireup_integration_starlette",
                original_parent="group_wireup_integration_starlette",
                group="wireup.integration.starlette",
                factory_name="wireup_task_factory",
            ),
        ),
        edges=(
            GraphEdge(
                id="edge_0",
                source="config_env",
                target="graph_demo_app_services_audit_AuditService",
                label="topic",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_1",
                source="config_env",
                target="graph_demo_app_services_session_RequestContextService",
                label="request_tag",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_2",
                source="config_env",
                target="graph_demo_app_services_session_RequestNonce",
                label="seed",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_3",
                source="config_env",
                target="graph_demo_app_services_weather_WeatherService",
                label="cache_key",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_4",
                source="config_infra",
                target="graph_demo_app_services_kv_MetricsClient",
                label="endpoint",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_5",
                source="config_infra",
                target="graph_demo_app_services_kv_RedisConnection",
                label="dsn",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_6",
                source="config_messaging",
                target="graph_demo_app_services_audit_AuditService",
                label="topic",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_7",
                source="config_messaging",
                target="graph_demo_app_services_session_RequestContextService",
                label="request_tag",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_8",
                source="config_services",
                target="graph_demo_app_factories_HttpClient",
                label="weather_url",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_9",
                source="config_services",
                target="graph_demo_app_services_weather_WeatherService",
                label="api_key",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_10",
                source="config_services",
                target="graph_demo_app_services_weather_WeatherService",
                label="cache_key",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_11",
                source="graph_demo_app_factories_HttpClient",
                target="graph_demo_app_services_weather_WeatherService",
                label="client",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_12",
                source="graph_demo_app_services_audit_AuditService",
                target="graph_demo_app_services_weather_WeatherService",
                label="audit",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_13",
                source="graph_demo_app_services_kv_KeyValueStore",
                target="graph_demo_app_services_audit_AuditService",
                label="kv_store",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_14",
                source="graph_demo_app_services_kv_KeyValueStore",
                target="graph_demo_app_services_weather_WeatherService",
                label="kv_store",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_15",
                source="graph_demo_app_services_kv_MetricsClient",
                target="graph_demo_app_services_kv_KeyValueStore",
                label="metrics",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_16",
                source="graph_demo_app_services_kv_RedisConnection",
                target="graph_demo_app_services_kv_KeyValueStore",
                label="redis",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_17",
                source="graph_demo_app_services_session_RequestContextService",
                target="consumer_GET_request_context",
                label="service",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_18",
                source="graph_demo_app_services_session_RequestNonce",
                target="graph_demo_app_services_session_RequestContextService",
                label="nonce",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_19",
                source="graph_demo_app_services_weather_WeatherService",
                target="consumer_GET_weather",
                label="service",
                kind="dependency",
            ),
            GraphEdge(
                id="edge_20",
                source="starlette_requests_Request",
                target="graph_demo_app_services_session_RequestContextService",
                label="request",
                kind="dependency",
            ),
        ),
    )
