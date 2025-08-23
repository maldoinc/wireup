from typing import Any, Iterator

import pytest
import wireup
import wireup.integration.litestar
from litestar import Controller, Litestar, Request, WebSocket, get, websocket
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


@service(lifetime="scoped")
class WebSocketContext:
    def __init__(self, socket: WebSocket[Any, Any, Any]) -> None:
        self.socket = socket


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


@websocket(path="/ws/wireup-websocket")
@inject
async def websocket_handler_wireup(
    socket: WebSocket[Any, Any, State],  # noqa: ARG001
    greeter: Injected[GreeterService],
    ctx: Injected[WebSocketContext],
) -> None:
    await ctx.socket.accept()
    recv = await ctx.socket.receive_json()
    await ctx.socket.send_json({"message": greeter.greet(recv["name"])})
    await ctx.socket.close()


class UserController(Controller):
    path = "/greet"

    @get()
    @inject
    async def greet(self, greeter: Injected[GreeterService]) -> str:
        return greeter.greet("User")


@pytest.fixture
def app() -> Litestar:
    app = Litestar([index, websocket_handler, websocket_handler_wireup, UserController])
    container = wireup.create_async_container(
        services=[RequestContext, WebSocketContext],
        service_modules=[shared_services, wireup.integration.litestar],
        type_normalizer=wireup.integration.litestar.litestar_type_normalizer,
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


@pytest.mark.parametrize("endpoint", ["/ws", "/ws/wireup-websocket"])
def test_websocket(endpoint: str, client: TestClient[Litestar]) -> None:
    with client.websocket_connect(endpoint) as ws:
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


def test_controller(client: TestClient[Litestar]) -> None:
    response = client.get("/greet")
    assert response.status_code == 200
    assert response.text == "Hello User"


async def test_executes_closes_container_lifespan() -> None:
    cleanup_done = False

    class Thing: ...

    @service
    def make_thing() -> Iterator[Thing]:
        yield Thing()
        nonlocal cleanup_done
        cleanup_done = True

    @get("/")
    @inject
    async def _thing_endpoint(thing: Injected[Thing]) -> str:
        assert isinstance(thing, Thing)
        return "Hello Thing"

    app = Litestar([_thing_endpoint])
    container = wireup.create_async_container(
        services=[make_thing],
        service_modules=[shared_services, wireup.integration.litestar],
    )
    wireup.integration.litestar.setup(container, app)

    with TestClient(app) as client:
        res = client.get("/")
        assert res.text == "Hello Thing"

    assert cleanup_done
