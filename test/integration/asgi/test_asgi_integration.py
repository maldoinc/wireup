from typing import Iterator

import pytest
import wireup
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from wireup import Injected, injectable
from wireup.errors import WireupError
from wireup.integration.asgi import WireupASGIMiddleware, get_request_container, inject


@injectable
class GreeterService:
    def greet(self, name: str) -> str:
        return f"Hello {name}"


def test_injects_dependencies_in_request_scope() -> None:
    @inject
    async def hello(request: Request, greeter: Injected[GreeterService]) -> PlainTextResponse:
        name = request.query_params.get("name", "World")
        return PlainTextResponse(greeter.greet(name))

    container = wireup.create_async_container(injectables=[GreeterService])
    app = Starlette(
        routes=[Route("/hello", hello, methods=["GET"])],
        middleware=[Middleware(WireupASGIMiddleware, container=container)],
    )

    with TestClient(app) as client:
        response = client.get("/hello", params={"name": "ASGI"})

    assert response.status_code == 200
    assert response.text == "Hello ASGI"


def test_get_request_container_outside_request_raises() -> None:
    with pytest.raises(WireupError, match="only available during an active HTTP/WebSocket request"):
        get_request_container()


def test_scoped_cleanup_after_request() -> None:
    cleaned_up = False

    class Resource:
        value = "ok"

    @injectable(lifetime="scoped")
    def make_resource() -> Iterator[Resource]:
        try:
            yield Resource()
        finally:
            nonlocal cleaned_up
            cleaned_up = True

    @inject
    def endpoint(_request: Request, resource: Injected[Resource]) -> PlainTextResponse:
        scoped = get_request_container()
        assert scoped._synchronous_get(Resource) is resource
        return PlainTextResponse(resource.value)

    container = wireup.create_async_container(injectables=[make_resource])
    app = Starlette(
        routes=[Route("/resource", endpoint, methods=["GET"])],
        middleware=[Middleware(WireupASGIMiddleware, container=container)],
    )

    with TestClient(app) as client:
        response = client.get("/resource")

    assert response.status_code == 200
    assert response.text == "ok"
    assert cleaned_up is True
