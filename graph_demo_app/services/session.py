from __future__ import annotations

from fastapi import Request
from typing_extensions import Annotated

from wireup import Inject, injectable


@injectable(lifetime="transient")
class RequestNonce:
    def __init__(self, seed: Annotated[str, Inject(config="env.name")]) -> None:
        self.seed = seed

    def value(self) -> str:
        return f"{self.seed}-nonce"


@injectable(lifetime="scoped")
class RequestContextService:
    def __init__(
        self,
        nonce: RequestNonce,
        request: Request,
        request_tag: Annotated[str, Inject(expr="${env.name}-${messaging.kafka.topic_prefix}")],
    ) -> None:
        self.nonce = nonce
        self.request = request
        self.request_tag = request_tag

    def snapshot(self) -> dict[str, str]:
        return {
            "nonce": self.nonce.value(),
            "request_path": self.request.url.path,
            "request_tag": self.request_tag,
        }
