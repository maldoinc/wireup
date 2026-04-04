from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import Annotated
from wireup import Inject, injectable

if TYPE_CHECKING:
    from test.unit.large_mermaid_app.factories import HttpClient
    from test.unit.large_mermaid_app.services.audit import AuditService
    from test.unit.large_mermaid_app.services.kv import KeyValueStore


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
