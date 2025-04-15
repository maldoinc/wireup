from dataclasses import dataclass

from fastapi import Request, WebSocket
from wireup import service


@service(lifetime="scoped")
@dataclass
class ServiceUsingFastapiRequest:
    req: Request


@service(lifetime="scoped")
@dataclass
class WSService:
    ws: WebSocket
