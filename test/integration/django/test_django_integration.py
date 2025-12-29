import os
import sys
from pathlib import Path

import django
import pytest
from django.test import AsyncClient, Client
from django.urls import include, path
from django.views.generic import TemplateView
from wireup.integration.django import WireupSettings
from wireup.integration.django.apps import get_app_container

from test.integration.django import view
from test.shared.shared_services.greeter import GreeterService

INSTALLED_APPS = [
    "wireup.integration.django",
    "test.integration.django.apps.app_1",
    "test.integration.django.apps.app_2",
]
DEBUG = True
ROOT_URLCONF = sys.modules[__name__]
WIREUP = WireupSettings(
    service_modules=[
        "test.shared.shared_services",
        "test.integration.django.injectable",
        "test.integration.django.factory",
    ]
)
SECRET_KEY = "not_actually_a_secret"  # noqa: S105
START_NUM = 4

MIDDLEWARE = ["wireup.integration.django.wireup_middleware"]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [Path(__file__).parent / "templates/"],
    },
]

urlpatterns = [
    path("", view.index),
    path("classbased", view.RandomNumberView.as_view()),
    path("async_classbased", view.AsyncRandomNumberView.as_view()),
    path("async_greet", view.async_greet),
    path("template_view/foo", TemplateView.as_view(template_name="foo.html")),
    path("template_view/bar", TemplateView.as_view(template_name="bar.html")),
    path("app_1", include("test.integration.django.apps.app_1.urls")),
    path("app_2", include("test.integration.django.apps.app_2.urls")),
]


@pytest.fixture(autouse=True, scope="module")
def django_setup() -> None:
    os.environ["DJANGO_SETTINGS_MODULE"] = "test.integration.django.test_django_integration"
    django.setup()


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def async_client() -> AsyncClient:
    return AsyncClient()


def test_django_thing(client: Client):
    res = client.get("/?name=World")

    assert res.status_code == 200
    assert res.content.decode("utf8") == "Hello World! Debug = True. Your lucky number is 4"


def test_get_random(client: Client):
    res = client.get("/classbased?name=Test")

    assert res.status_code == 200
    assert res.content.decode("utf8") == "Hello Test! Debug = True. Your lucky number is 4"


@pytest.mark.parametrize("path", ("foo", "bar"))
def test_get_templated_views(client: Client, path: str):
    res = client.get(f"/template_view/{path}")

    assert res.status_code == 200
    assert res.content.decode("utf8") == path


def test_override(client: Client):
    class RudeGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Bad day to you, {name}"

    with get_app_container().override.injectable(GreeterService, new=RudeGreeter()):
        res = client.get("/classbased?name=Test")

    assert res.status_code == 200
    assert res.content.decode("utf8") == "Bad day to you, Test! Debug = True. Your lucky number is 4"


def test_multiple_apps(client: Client):
    app_1_response = client.get("/app_1/?name=World")

    assert app_1_response.status_code == 200
    assert app_1_response.content.decode("utf8") == "App 1: Hello World"

    app_2_response = client.get("/app_2/?name=World")

    assert app_2_response.status_code == 200
    assert app_2_response.content.decode("utf8") == "App 2: Hello World"


async def test_async_view_with_async_service(async_client: AsyncClient):
    # GIVEN an async Django view with an injected async injectable
    # WHEN making a request
    res = await async_client.get("/async_greet?name=World")

    # THEN the async injectable is properly injected and works
    assert res.status_code == 200
    assert res.content.decode("utf8") == "Hello World! Debug = True"


async def test_async_cbv_with_async_service(async_client: AsyncClient):
    # GIVEN an async Django CBV with an injected async injectable
    # WHEN making a request
    res = await async_client.get("/async_classbased?name=World")

    # THEN the async injectable is properly injected and works
    assert res.status_code == 200
    assert res.content.decode("utf8") == "Hello World! Debug = True. Your lucky number is 4"
