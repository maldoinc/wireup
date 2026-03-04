from typing import Iterator
from uuid import uuid4

import pytest
import wireup
import wireup.integration.starlette
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.endpoints import HTTPEndpoint
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route, WebSocketRoute
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket
from wireup._annotations import Injected, injectable
from wireup.integration.starlette import WireupTask, get_app_container, get_request_container, inject

from test.shared import shared_services
from test.shared.shared_services.greeter import GreeterService


@injectable(lifetime="scoped")
class RequestContext:
    def __init__(self, request: Request):
        self.request = request

    @property
    def name(self) -> str:
        return self.request.query_params.get("name", "World")


@injectable(lifetime="scoped")
class WebSocketContext:
    def __init__(self, websocket: WebSocket, greeter: GreeterService):
        self.websocket = websocket
        self.greeter = greeter

    async def handle(self) -> None:
        await self.websocket.accept()

        data = await self.websocket.receive_text()
        await self.websocket.send_text(self.greeter.greet(data))
        await self.websocket.close()


class HelloEndpoint(HTTPEndpoint):
    @inject
    async def get(
        self,
        _request: Request,
        request_context: Injected[RequestContext],
        greeter: Injected[GreeterService],
    ) -> PlainTextResponse:
        return PlainTextResponse(greeter.greet(request_context.name))


@inject
async def hello(
    _request: Request,
    request_context: Injected[RequestContext],
    greeter: Injected[GreeterService],
) -> PlainTextResponse:
    return PlainTextResponse(greeter.greet(request_context.name))


@inject
async def hello_websocket(_websocket: WebSocket, websocket_context: Injected[WebSocketContext]) -> None:
    await websocket_context.handle()


def create_app():
    container = wireup.create_async_container(
        injectables=[RequestContext, WebSocketContext, shared_services, wireup.integration.starlette],
        config={"foo": "bar"},
    )

    app = Starlette(
        routes=[
            Route("/hello", hello, methods=["GET"]),
            Route("/hello_endpoint", HelloEndpoint, methods=["GET"]),
            WebSocketRoute("/ws", hello_websocket),
        ],
    )

    wireup.integration.starlette.setup(container, app)

    return app


@pytest.fixture()
def app() -> Starlette:
    return create_app()


@pytest.fixture()
def client(app: Starlette) -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("endpoint", ["/hello", "/hello_endpoint"])
def test_injects_routes(client: TestClient, endpoint: str) -> None:
    response = client.get(endpoint, params={"name": "Starlette"})
    assert response.text == "Hello Starlette"
    assert response.status_code == 200


def test_injects_websocket(client: TestClient) -> None:
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("World")
        data = websocket.receive_text()
        assert data == "Hello World"


def test_override(app: Starlette, client: TestClient):
    class UppercaseGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return super().greet(name).upper()

    with get_app_container(app).override.injectable(GreeterService, new=UppercaseGreeter()):
        response = client.get("/hello", params={"name": "Test"})

    assert response.text == "HELLO TEST"
    assert response.status_code == 200


def test_get_request_container_in_middleware() -> None:
    class StarletteTestMiddleware:
        def __init__(self, app: ASGIApp) -> None:
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] not in {"http", "websocket"}:
                return await self.app(scope, receive, send)

            container = get_request_container()
            ctx = await container.get(RequestContext)
            msg = f"RequestContext name: {ctx.name}"
            raise ValueError(msg)

    container = wireup.create_async_container(
        injectables=[RequestContext, WebSocketContext, shared_services, wireup.integration.starlette],
    )

    app = Starlette(
        routes=[Route("/hello", hello, methods=["GET"])],
        middleware=[Middleware(StarletteTestMiddleware)],
    )

    wireup.integration.starlette.setup(container, app)

    client = TestClient(app)
    with pytest.raises(ValueError, match="RequestContext name: World"):
        client.get("/hello", params={"name": "World"})


async def test_executes_closes_container_lifespan() -> None:
    cleanup_done = False

    class Thing: ...

    @injectable
    def make_thing() -> Iterator[Thing]:
        yield Thing()
        nonlocal cleanup_done
        cleanup_done = True

    @inject
    def hello(_request: Request, thing: Injected[Thing]) -> PlainTextResponse:
        assert isinstance(thing, Thing)
        return PlainTextResponse("Hello World")

    app = Starlette(routes=[Route("/hello", hello, methods=["GET"])])
    container = wireup.create_async_container(injectables=[make_thing])
    wireup.integration.starlette.setup(container, app)

    with TestClient(app) as client:
        client.get("/hello")

    assert cleanup_done


def test_injects_background_tasks() -> None:
    task_result: list[str] = []

    def write_logs(name: str, greeter: Injected[GreeterService]) -> None:
        task_result.append(greeter.greet(name))

    @inject
    async def hello_with_background_task(
        _request: Request,
        wireup_task: Injected[WireupTask],
    ) -> PlainTextResponse:
        return PlainTextResponse(
            "ok",
            background=BackgroundTask(wireup_task(write_logs), "Starlette"),
        )

    app = Starlette(routes=[Route("/hello_bg", hello_with_background_task, methods=["GET"])])
    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.starlette])
    wireup.integration.starlette.setup(container, app)

    with TestClient(app) as client:
        response = client.get("/hello_bg")

    assert response.status_code == 200
    assert task_result == ["Hello Starlette"]


def test_injects_background_async_tasks() -> None:
    task_result: list[str] = []

    async def write_logs(name: str, greeter: Injected[GreeterService]) -> None:
        task_result.append(greeter.greet(name))

    @inject
    async def hello_with_background_task(
        _request: Request,
        wireup_task: Injected[WireupTask],
    ) -> PlainTextResponse:
        return PlainTextResponse(
            "ok",
            background=BackgroundTask(wireup_task(write_logs), "Async"),
        )

    app = Starlette(routes=[Route("/hello_bg", hello_with_background_task, methods=["GET"])])
    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.starlette])
    wireup.integration.starlette.setup(container, app)

    with TestClient(app) as client:
        response = client.get("/hello_bg")

    assert response.status_code == 200
    assert task_result == ["Hello Async"]


def test_background_task_uses_different_scope_than_request() -> None:
    ids: dict[str, str] = {}

    @injectable(lifetime="scoped")
    class ScopedContext:
        def __init__(self) -> None:
            self.id = uuid4().hex

    def write_logs(scoped_context: Injected[ScopedContext]) -> None:
        ids["task"] = scoped_context.id

    @inject
    async def hello_with_background_task(
        _request: Request,
        scoped_context: Injected[ScopedContext],
        wireup_task: Injected[WireupTask],
    ) -> PlainTextResponse:
        ids["request"] = scoped_context.id
        return PlainTextResponse(
            "ok",
            background=BackgroundTask(wireup_task(write_logs)),
        )

    app = Starlette(routes=[Route("/hello_bg", hello_with_background_task, methods=["GET"])])
    container = wireup.create_async_container(
        injectables=[ScopedContext, shared_services, wireup.integration.starlette],
    )
    wireup.integration.starlette.setup(container, app)

    with TestClient(app) as client:
        response = client.get("/hello_bg")

    assert response.status_code == 200
    assert ids["request"] != ids["task"]
