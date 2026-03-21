from __future__ import annotations

import wireup
import wireup.integration.fastapi as wireup_fastapi
from fastapi import FastAPI
from wireup.integration.fastapi import GraphEndpointOptions, setup

from graph_demo_app import factories, services
from graph_demo_app.cbr import DemoClassBasedHandler
from graph_demo_app.services.audit import AuditService
from graph_demo_app.services.session import RequestContextService
from graph_demo_app.services.weather import WeatherService

app = FastAPI(title="Wireup Graph Demo")


@app.get("/")
async def index() -> dict[str, str]:
    return {
        "message": "Visit /weather, /audit, /request-context, /class-based/summary, or /_wireup",
    }


@app.get("/weather")
async def weather(service: wireup.Injected[WeatherService]) -> dict[str, str]:
    return service.snapshot()


@app.get("/audit")
async def audit_trail(service: wireup.Injected[AuditService]) -> dict[str, str]:
    return service.describe()


@app.get("/request-context")
async def request_context(service: wireup.Injected[RequestContextService]) -> dict[str, str]:
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

setup(
    container,
    app,
    class_based_handlers=[DemoClassBasedHandler],
    graph_endpoint=GraphEndpointOptions(enabled=True, base_module="graph_demo_app"),
)
