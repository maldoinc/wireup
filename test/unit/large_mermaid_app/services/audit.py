from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import Annotated
from wireup import Inject, injectable

if TYPE_CHECKING:
    from test.unit.large_mermaid_app.services.kv import KeyValueStore


@injectable
class AuditService:
    def __init__(
        self,
        kv_store: KeyValueStore,
        topic: Annotated[str, Inject(expr="${messaging.kafka.topic_prefix}-${env.name}")],
    ) -> None:
        self.kv_store = kv_store
        self.topic = topic
