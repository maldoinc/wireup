import pytest
import wireup
import wireup.integration.starlette
from fastapi.responses import PlainTextResponse
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.routing import Route
from starlette.testclient import TestClient
from wireup._annotations import Injected
from wireup.integration.starlette import get_app_container, inject

from test.shared import shared_services
from test.shared.shared_services.greeter import GreeterService


class HelloEndpoint(HTTPEndpoint):
    @inject
    async def get(self, request: Request, greeter: Injected[GreeterService]) -> PlainTextResponse:
        return PlainTextResponse(greeter.greet(request.query_params.get("name", "World")))


@inject
async def hello(request: Request, greeter: Injected[GreeterService]) -> PlainTextResponse:
    return PlainTextResponse(greeter.greet(request.query_params.get("name", "World")))


def create_app():
    container = wireup.create_async_container(
        service_modules=[shared_services],
        parameters={"foo": "bar"},
    )

    app = Starlette(
        routes=[
            Route("/hello", hello, methods=["GET"]),
            Route("/hello_endpoint", HelloEndpoint, methods=["GET"]),
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
def test_app(client: TestClient, endpoint: str) -> None:
    response = client.get(endpoint, params={"name": "Starlette"})
    assert response.text == "Hello Starlette"
    assert response.status_code == 200


def test_override(app: Starlette, client: TestClient):
    class UppercaseGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return super().greet(name).upper()

    with get_app_container(app).override.service(GreeterService, new=UppercaseGreeter()):
        response = client.get("/hello", params={"name": "Test"})

    assert response.text == "HELLO TEST"
    assert response.status_code == 200
