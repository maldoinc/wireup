import os
import sys

import django
import pytest
import strawberry
from django.test import Client
from django.urls import path
from strawberry.django.views import GraphQLView
from wireup._annotations import Injected
from wireup.integration.django import WireupSettings, inject

from test.shared.shared_services.greeter import GreeterService

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "wireup.integration.django",
]
DEBUG = True
ROOT_URLCONF = sys.modules[__name__]
WIREUP = WireupSettings(service_modules=["test.shared.shared_services"])
SECRET_KEY = "not_actually_a_secret"  # noqa: S105
MIDDLEWARE = ["wireup.integration.django.wireup_middleware"]
urlpatterns = []


@pytest.fixture(autouse=True, scope="module")
def django_setup() -> None:
    os.environ["DJANGO_SETTINGS_MODULE"] = "test.integration.strawberry.test_strawberry_django_usage"
    django.setup()

    if urlpatterns:
        return

    @strawberry.type
    class Query:
        @strawberry.field
        @inject
        def hello(self, greeter: Injected[GreeterService], name: str = "World") -> str:
            return greeter.greet(name)

    schema = strawberry.Schema(query=Query)
    urlpatterns.append(path("graphql", GraphQLView.as_view(schema=schema)))


@pytest.fixture
def client() -> Client:
    return Client()


def test_django_runtime_injects_resolvers(client: Client) -> None:
    response = client.post("/graphql", data={"query": '{ hello(name: "Django") }'}, content_type="application/json")
    assert response.status_code == 200
    assert response.json()["data"] == {"hello": "Hello Django"}


def test_django_runtime_hides_injected_args_from_schema(client: Client) -> None:
    response = client.post(
        "/graphql",
        data={
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
        content_type="application/json",
    )
    assert response.status_code == 200
    fields = response.json()["data"]["__type"]["fields"]
    by_name = {field["name"]: [arg["name"] for arg in field["args"]] for field in fields}
    assert by_name["hello"] == ["name"]
