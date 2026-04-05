from __future__ import annotations

from typing_extensions import Annotated

from wireup import Inject, injectable

from graph_demo_app.services.kv import KeyValueStore


@injectable
class AuditService:
    def __init__(
        self,
        kv_store: KeyValueStore,
        topic: Annotated[str, Inject(expr="${messaging.kafka.topic_prefix}-${env.name}")],
    ) -> None:
        self.kv_store = kv_store
        self.topic = topic

    def describe(self) -> dict[str, str]:
        return {"topic": self.topic}
