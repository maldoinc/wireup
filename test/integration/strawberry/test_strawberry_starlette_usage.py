import strawberry
import wireup
import wireup.integration.starlette
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount
from starlette.testclient import TestClient
from strawberry.asgi import GraphQL
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


def create_app() -> Starlette:
    container = wireup.create_async_container(
        injectables=[HeaderReader, shared_services, wireup.integration.starlette],
    )
    schema = strawberry.Schema(query=Query)
    app = Starlette(routes=[Mount("/", app=GraphQL(schema))])
    wireup.integration.starlette.setup(container, app)
    return app


def test_starlette_runtime_injects_resolvers() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/", json={"query": "{ hello fromHeader }"}, headers={"x-name": "Wireup"})
        assert response.status_code == 200
        assert response.json()["data"] == {"hello": "Hello World", "fromHeader": "Wireup"}


def test_starlette_runtime_hides_injected_args_from_schema() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/",
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
