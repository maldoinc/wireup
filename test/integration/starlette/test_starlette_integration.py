import pytest
import wireup
import wireup.integration.starlette
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from wireup._annotations import Injected

from test.shared import shared_services
from test.shared.shared_services.greeter import GreeterService


def create_app():
    async def hello(request: Request, greeter: Injected[GreeterService]):
        return JSONResponse({"message": greeter.greet(request.query_params.get("name", "World"))})

    container = wireup.create_async_container(
        service_modules=[shared_services],
        parameters={"foo": "bar"},
    )
    inject = wireup.inject_from_container(container)

    app = Starlette(routes=[Route("/hello", inject(hello), methods=["GET"])])

    wireup.integration.starlette.setup(container, app)

    return app


@pytest.fixture()
def app() -> Starlette:
    return create_app()


@pytest.fixture()
def client(app: Starlette) -> TestClient:
    return TestClient(app)


def test_app(app: Starlette):
    client = TestClient(app)
    response = client.get("/hello")
    assert response.status_code == 200
