from __future__ import annotations

from typing import Any

import fastapi
import wireup

from graph_demo_app.services.audit import AuditService
from graph_demo_app.services.session import RequestContextService


class DemoClassBasedHandler:
    router = fastapi.APIRouter(prefix="/class-based")

    def __init__(self, audit_service: AuditService) -> None:
        self.audit_service = audit_service

    @router.get("/summary")
    async def summary(
        self,
        request_context: wireup.Injected[RequestContextService],
    ) -> dict[str, Any]:
        return {
            "topic": self.audit_service.topic,
            "request_context": request_context.snapshot(),
        }
