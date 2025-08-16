from typing import Any, Iterator

import pytest
import wireup
import wireup.integration.litestar
from litestar import Litestar, Request, WebSocket, get, websocket
from litestar.datastructures import State
from litestar.testing import TestClient
from wireup._annotations import Injected, service
from wireup.integration.litestar import get_app_container, inject

from test.shared import shared_services
from test.shared.shared_services.greeter import GreeterService


@service(lifetime="scoped")
class RequestContext:
    def __init__(self, request: Request[Any, Any, Any]) -> None:
        self.request = request

    @property
    def name(self) -> str:
        return self.request.query_params["name"]


@get("/")
@inject
async def index(greeter: Injected[GreeterService], ctx: Injected[RequestContext]) -> str:
    return greeter.greet(ctx.name)


@websocket(path="/ws")
@inject
async def websocket_handler(greeter: Injected[GreeterService], socket: WebSocket[Any, Any, State]) -> None:
    await socket.accept()
    recv = await socket.receive_json()
    await socket.send_json({"message": greeter.greet(recv["name"])})
    await socket.close()


@pytest.fixture
def app() -> Litestar:
    app = Litestar([index, websocket_handler], middleware=[wireup.integration.litestar.wireup_middleware])
    container = wireup.create_async_container(
        services=[RequestContext],
        service_modules=[shared_services, wireup.integration.litestar],
    )
    wireup.integration.litestar.setup(container, app)
    return app


@pytest.fixture
def client(app: Litestar) -> Iterator[TestClient[Litestar]]:
    with TestClient(app) as test_client:
        yield test_client


def test_index(client: TestClient[Litestar]) -> None:
    response = client.get("/", params={"name": "World"})
    assert response.status_code == 200
    assert response.text == "Hello World"


def test_websocket(client: TestClient[Litestar]) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"name": "websockets"})
        data = ws.receive_json()
        assert data == {"message": "Hello websockets"}


def test_override(app: Litestar, client: TestClient[Litestar]):
    class UppercaseGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return super().greet(name).upper()

    with get_app_container(app).override.service(GreeterService, new=UppercaseGreeter()):
        response = client.get("/", params={"name": "Test"})

    assert response.text == "HELLO TEST"
    assert response.status_code == 200
