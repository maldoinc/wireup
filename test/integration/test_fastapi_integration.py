import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Dict

import anyio.to_thread
import pytest
import wireup
import wireup.integration
import wireup.integration.fastapi
from fastapi import Depends, FastAPI, Request, WebSocket
from fastapi.testclient import TestClient
from typing_extensions import Annotated
from wireup import Inject
from wireup.errors import UnknownServiceRequestedError, WireupError
from wireup.integration.fastapi import WireupContainer, WireupExpr, WireupParameter, WireupService, get_container
from wireup.ioc.dependency_container import DependencyContainer
from wireup.ioc.types import ServiceLifetime

from test.unit.services.no_annotations.random.random_service import RandomService


@dataclass
class ServiceUsingFastapiRequest:
    req: Request


def get_lucky_number() -> int:
    # Raise if this will be invoked more than once
    # That would be the case if wireup also "unwraps" and tries
    # to resolve dependencies it doesn't own.
    if hasattr(get_lucky_number, "_called"):
        raise Exception("Lucky Number was already invoked")

    get_lucky_number._called = True  # type: ignore[reportFunctionMemberAccess]
    return 42


class GreeterService:
    def greet(self, name: str) -> str:
        return f"Hello {name}"


def get_greeting(
    greeter: Annotated[GreeterService, WireupService(GreeterService)],
    name: str,
) -> str:
    return greeter.greet(name)


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/lucky-number")
    async def lucky_number_route(
        random_service: Annotated[RandomService, Inject()], lucky_number: Annotated[int, Depends(get_lucky_number)]
    ):
        return {"number": random_service.get_random(), "lucky_number": lucky_number}

    @app.get("/rng")
    async def rng_route(random_service: Annotated[RandomService, Inject()]):
        return {"number": random_service.get_random()}

    @app.get("/wireup-in-fastapi")
    async def rng_route(
        greeting: Annotated[str, Depends(get_greeting)],
        foo_param: Annotated[str, WireupParameter("foo")],
        foo_foo: Annotated[str, WireupExpr("${foo}-${foo}")],
        container: Annotated[DependencyContainer, WireupContainer()],
    ):
        assert foo_param == "bar"
        assert foo_foo == "bar-bar"
        assert isinstance(container, DependencyContainer)

        return {"greeting": greeting}

    @app.get("/params")
    async def params_route(
        foo: Annotated[str, Inject(param="foo")], foo_foo: Annotated[str, Inject(expr="${foo}-${foo}")]
    ):
        return {"foo": foo, "foo_foo": foo_foo}

    @app.get("/raise-unknown")
    async def raise_unknown(_unknown_service: Annotated[None, Inject()]):
        return {"msg": "Hello World"}

    @app.get("/current-request")
    async def curr_request(_request: Request, req: Annotated[ServiceUsingFastapiRequest, Inject()]) -> Dict[str, Any]:
        return {"foo": req.req.query_params["foo"], "request_id": req.req.headers["X-Request-Id"]}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket, greeter: Annotated[GreeterService, Inject()]):
        await websocket.accept()
        data = await websocket.receive_text()
        await websocket.send_text(greeter.greet(data))
        await websocket.close()

    container = wireup.create_container(service_modules=[], parameters={"foo": "bar"})
    container.register(RandomService)
    container.register(GreeterService)
    container.register(ServiceUsingFastapiRequest, lifetime=ServiceLifetime.TRANSIENT)
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


def test_injects_wireup_in_fastapi_depends(client: TestClient):
    response = client.get("/wireup-in-fastapi", params={"name": "World"})
    assert response.status_code == 200
    assert response.json() == {"greeting": "Hello World"}


def test_override(app: FastAPI, client: TestClient):
    class RealRandom(RandomService):
        def get_random(self) -> int:
            return super().get_random() ** 2

    with get_container(app).override.service(RandomService, new=RealRandom()):
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


def test_raises_request_outside_of_scope(app: FastAPI) -> None:
    with pytest.raises(WireupError, match="fastapi.Request in wireup is only available during a request."):
        get_container(app).get(Request)
