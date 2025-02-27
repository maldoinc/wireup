import asyncio
import uuid

import anyio.to_thread
import pytest
import wireup
import wireup.integration
import wireup.integration.fastapi
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from wireup.errors import UnknownServiceRequestedError, WireupError
from wireup.integration.fastapi import get_app_container

from test.integration.fastapi import services as fastapi_test_services
from test.integration.fastapi.router import router
from test.shared import shared_services
from test.shared.shared_services.rand import RandomService


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    container = wireup.create_async_container(
        service_modules=[fastapi_test_services, shared_services], parameters={"foo": "bar"}
    )
    wireup.integration.fastapi.setup(container, app)

    return app


@pytest.fixture()
def app() -> FastAPI:
    return create_app()


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_injects_service(client: TestClient):
    response = client.get("/lucky-number")
    assert response.status_code == 200
    assert response.json() == {"number": 4, "lucky_number": 42}


def test_scoped(client: TestClient):
    response = client.get("/scoped")
    assert response.status_code == 200


def test_override(app: FastAPI, client: TestClient):
    class RealRandom(RandomService):
        def get_random(self) -> int:
            return super().get_random() ** 2

    with get_app_container(app).override.service(RandomService, new=RealRandom()):
        response = client.get("/rng")
    assert response.status_code == 200
    assert response.json() == {"number": 16}


def test_injects_parameters(client: TestClient):
    response = client.get("/params")
    assert response.status_code == 200
    assert response.json() == {"foo": "bar", "foo_foo": "bar-bar"}


def test_websocket(client: TestClient):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("World")
        data = websocket.receive_text()
        assert data == "Hello World"


async def test_current_request_service(client: TestClient):
    async def _make_request():
        request_id = uuid.uuid4().hex
        response = await anyio.to_thread.run_sync(
            lambda: client.get("/current-request", params={"foo": request_id}, headers={"X-Request-Id": request_id})
        )
        assert response.status_code == 200
        assert response.json() == {"foo": request_id, "request_id": request_id}

    await asyncio.gather(*(_make_request() for _ in range(100)))


def test_raises_on_unknown_service(client: TestClient):
    with pytest.raises(
        UnknownServiceRequestedError,
        match="Cannot wire unknown class <class 'NoneType'>. Use '@service' or '@abstract' to enable autowiring.",
    ):
        client.get("/raise-unknown")


async def test_raises_request_outside_of_scope(app: FastAPI) -> None:
    with pytest.raises(WireupError, match="fastapi.Request in wireup is only available during a request."):
        async with get_app_container(app).enter_scope() as scoped:
            await scoped.get(Request)
