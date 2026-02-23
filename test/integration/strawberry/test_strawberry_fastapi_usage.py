import strawberry
import wireup
import wireup.integration.fastapi
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from strawberry.fastapi import GraphQLRouter
from wireup._annotations import Injected, injectable
from wireup.integration.starlette import inject

from test.shared import shared_services
from test.shared.shared_services.greeter import GreeterService


@injectable(lifetime="scoped")
class HeaderReader:
    def __init__(self, request: Request):
        self.request = request


@strawberry.type
class Query:
    @strawberry.field
    @inject
    def hello(self, greeter: Injected[GreeterService]) -> str:
        return greeter.greet("World")

    @strawberry.field
    @inject
    def from_header(self, header_reader: Injected[HeaderReader]) -> str:
        return header_reader.request.headers.get("x-name", "missing")


def create_app(*, middleware_mode: bool) -> FastAPI:
    container = wireup.create_async_container(
        injectables=[HeaderReader, shared_services, wireup.integration.fastapi],
    )
    schema = strawberry.Schema(query=Query)
    app = FastAPI()
    app.include_router(GraphQLRouter(schema), prefix="/graphql")
    wireup.integration.fastapi.setup(container, app, middleware_mode=middleware_mode)
    return app


def test_fastapi_runtime_injects_resolvers() -> None:
    with TestClient(create_app(middleware_mode=True)) as client:
        response = client.post("/graphql", json={"query": "{ hello fromHeader }"}, headers={"x-name": "Wireup"})
        assert response.status_code == 200
        assert response.json()["data"] == {"hello": "Hello World", "fromHeader": "Wireup"}


def test_fastapi_runtime_hides_injected_args_from_schema() -> None:
    with TestClient(create_app(middleware_mode=True)) as client:
        response = client.post(
            "/graphql",
            json={
                "query": """
                {
                  __type(name: "Query") {
                    fields {
                      name
                      args {
                        name
                      }
                    }
                  }
                }
                """
            },
        )
        assert response.status_code == 200
        fields = response.json()["data"]["__type"]["fields"]
        by_name = {field["name"]: [arg["name"] for arg in field["args"]] for field in fields}
        assert by_name["hello"] == []
        assert by_name["fromHeader"] == []


def test_fastapi_runtime_requires_middleware_mode_for_resolver_inject() -> None:
    # Without middleware_mode=True, the Starlette/FastAPI request context used by @inject is unavailable.
    with TestClient(create_app(middleware_mode=False), raise_server_exceptions=False) as client:
        response = client.post("/graphql", json={"query": "{ hello }"})
        body = response.json()
        assert response.status_code == 200
        assert "errors" in body
