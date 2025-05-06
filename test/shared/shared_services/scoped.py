from dataclasses import dataclass

from fastapi import WebSocket
from wireup import service


@service(lifetime="scoped")
class ScopedServiceDependency: ...


@service(lifetime="scoped")
@dataclass
class ScopedService:
    other: ScopedServiceDependency


@service(lifetime="scoped")
@dataclass
class ScopedWebsocketService:
    other: WebSocket
