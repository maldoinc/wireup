import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Dict

import anyio.to_thread
import pytest
import wireup
import wireup.integration
import wireup.integration.fastapi
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from typing_extensions import Annotated
from wireup import Inject
from wireup.errors import UnknownServiceRequestedError
from wireup.integration.fastapi import get_container
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


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/lucky-number")
    async def _(
        random_service: Annotated[RandomService, Inject()], lucky_number: Annotated[int, Depends(get_lucky_number)]
    ):
        return {"number": random_service.get_random(), "lucky_number": lucky_number}

    @app.get("/rng")
    async def _(random_service: Annotated[RandomService, Inject()]):
        return {"number": random_service.get_random()}

    @app.get("/params")
    async def _(foo: Annotated[str, Inject(param="foo")], foo_foo: Annotated[str, Inject(expr="${foo}-${foo}")]):
        return {"foo": foo, "foo_foo": foo_foo}

    @app.get("/raise-unknown")
    async def _(_unknown_service: Annotated[None, Inject()]):
        return {"msg": "Hello World"}

    @app.get("/current-request")
    async def _(_request: Request, req: Annotated[ServiceUsingFastapiRequest, Inject()]) -> Dict[str, Any]:
        return {"foo": req.req.query_params["foo"], "request_id": req.req.headers["X-Request-Id"]}

    container = wireup.create_container(service_modules=[], parameters={"foo": "bar"})
    container.register(RandomService)
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
