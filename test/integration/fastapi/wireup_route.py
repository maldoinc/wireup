from fastapi import APIRouter, WebSocket
from wireup import Injected
from wireup.integration.fastapi import WireupRoute

from test.integration.fastapi.services import ScopedWebsocketService
from test.shared.shared_services.greeter import GreeterService
from test.shared.shared_services.scoped import ScopedService, ScopedServiceDependency

router = APIRouter(route_class=WireupRoute)


def get_int() -> int:
    return 1


@router.get("/scoped/wireup_injected")
async def scoped_route_wireup_injected(
    scoped_service: Injected[ScopedService],
    scoped_service2: Injected[ScopedService],
    scoped_service_dependency: Injected[ScopedServiceDependency],
):
    assert scoped_service is scoped_service2
    assert scoped_service.other is scoped_service_dependency


@router.websocket("/ws/wireup_injected")
async def websocket_endpoint_wireup_injected(
    websocket: WebSocket,
    greeter: Injected[GreeterService],
    scoped_service: Injected[ScopedService],
    scoped_service2: Injected[ScopedService],
    scoped_service_dependency: Injected[ScopedServiceDependency],
    scoped_websocket_service: Injected[ScopedWebsocketService],
):
    assert scoped_service is scoped_service2
    assert scoped_service.other is scoped_service_dependency
    assert scoped_websocket_service.other is websocket

    await websocket.accept()
    data = await websocket.receive_text()
    await websocket.send_text(greeter.greet(data))
    await websocket.close()
