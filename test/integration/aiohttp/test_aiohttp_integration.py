from typing import Awaitable, Callable

import pytest
import wireup
import wireup.integration
import wireup.integration.aiohttp
from aiohttp import web
from aiohttp.test_utils import TestClient

from test.integration.aiohttp import handler, routes
from test.integration.aiohttp import services as aio_test_services
from test.shared import shared_services


def create_app() -> web.Application:
    app = web.Application()

    app.router.add_routes(routes.router)
    app.router.add_routes(handler.WireupTestHandler.router)

    container = wireup.create_async_container(
        service_modules=[shared_services, aio_test_services, wireup.integration.aiohttp]
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


async def test_handler(client: TestClient) -> None:
    res = await client.get("/handler/greet?name=Handler")
    body = await res.json()
    assert body == {"greeting": "Hello Handler", "counter": 1}

    res = await client.get("/handler/greet?name=Aio")
    body = await res.json()
    assert body == {"greeting": "Hello Aio", "counter": 2}
