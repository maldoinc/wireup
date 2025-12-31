from dataclasses import dataclass

from fastapi import Request, WebSocket
from wireup import injectable


@injectable(lifetime="scoped")
@dataclass
class ServiceUsingFastapiRequest:
    req: Request


@injectable(lifetime="scoped")
@dataclass
class WSService:
    ws: WebSocket


@dataclass
@injectable(lifetime="scoped")
class WebsocketInjectedGreeterService:
    websocket: WebSocket

    async def greet(self):
        await self.websocket.accept()
        data = await self.websocket.receive_text()
        await self.websocket.send_text(f"Hello {data}")
        await self.websocket.close()


@injectable(lifetime="scoped")
@dataclass
class ScopedWebsocketService:
    other: WebSocket
