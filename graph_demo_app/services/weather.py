from __future__ import annotations

from typing_extensions import Annotated

from wireup import Inject, injectable

from graph_demo_app.factories import HttpClient
from graph_demo_app.services.audit import AuditService
from graph_demo_app.services.kv import KeyValueStore


@injectable
class WeatherService:
    def __init__(
        self,
        api_key: Annotated[str, Inject(config="services.weather.api_key")],
        client: HttpClient,
        kv_store: KeyValueStore,
        audit: AuditService,
        cache_key: Annotated[str, Inject(expr="${env.name}-${services.weather.cache_suffix}")],
    ) -> None:
        self.api_key = api_key
        self.client = client
        self.kv_store = kv_store
        self.audit = audit
        self.cache_key = cache_key

    def snapshot(self) -> dict[str, str]:
        return {
            "api_key": self.api_key,
            "client": self.client.describe(),
            "cache_key": self.cache_key,
            "topic": self.audit.topic,
        }
