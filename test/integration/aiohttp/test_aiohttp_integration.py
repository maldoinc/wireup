from typing import Awaitable, Callable

import pytest
import wireup
import wireup.integration
import wireup.integration.aiohttp
from aiohttp import web
from aiohttp.test_utils import TestClient
from wireup.integration.aiohttp import get_app_container

from test.integration.aiohttp import handler, routes
from test.integration.aiohttp import services as aio_test_services
from test.shared import shared_services
from test.shared.shared_services.greeter import GreeterService


class CustomGreeter(GreeterService):
    def greet(self, name: str) -> str:
        return f"Hoi, {name}"


def create_app() -> web.Application:
    app = web.Application()

    app.router.add_routes(routes.router)

    container = wireup.create_async_container(
        injectables=[shared_services, aio_test_services, wireup.integration.aiohttp]
    )
    wireup.integration.aiohttp.setup(container, app, handlers=[handler.WireupTestHandler])

    return app


@pytest.fixture()
def app() -> web.Application:
    return create_app()


@pytest.fixture()
async def client(
    app: web.Application, aiohttp_client: Callable[[web.Application], Awaitable[TestClient]]
) -> TestClient:
    return await aiohttp_client(app)


async def test_hello(client: TestClient) -> None:
    res = await client.get("/greeting")
    body = await res.json()
    assert body == {"greeting": "Hello world"}


async def test_inject_request(client: TestClient) -> None:
    res = await client.get("/inject_request")
    assert res.status == 200


async def test_webview(client: TestClient) -> None:
    res = await client.get("/webview")
    body = await res.json()
    assert body == {"greeting": "Hello webview"}


async def test_override(client: TestClient, app: web.Application) -> None:
    with get_app_container(app).override.injectable(GreeterService, new=CustomGreeter()):
        res = await client.get("/webview")
        body = await res.json()
        assert body == {"greeting": "Hoi, webview"}


async def test_handler(client: TestClient) -> None:
    res = await client.get("/handler/greet?name=Handler")
    body = await res.json()
    assert body == {"greeting": "Hello Handler", "counter": 1}

    res = await client.get("/handler/greet?name=Aio")
    body = await res.json()
    assert body == {"greeting": "Hello Aio", "counter": 2}


async def test_handler_override(aiohttp_client: Callable[[web.Application], Awaitable[TestClient]]) -> None:
    app = create_app()
    container = get_app_container(app)

    with container.override.injectable(GreeterService, new=CustomGreeter()):
        client = await aiohttp_client(app())

        res = await client.get("/handler/greet?name=Handler")
        body = await res.json()
        assert body == {"greeting": "Hoi, Handler", "counter": 1}
