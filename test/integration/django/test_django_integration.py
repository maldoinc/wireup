import os
import sys
from pathlib import Path

import django
import pytest
from django.test import Client
from django.urls import include, path
from django.views.generic import TemplateView
from wireup.errors import WireupError
from wireup.integration.django import WireupSettings, inject
from wireup.integration.django.apps import get_app_container

from test.integration.django import view
from test.shared.shared_services.greeter import GreeterService

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "wireup.integration.django",
    "test.integration.django.apps.app_1",
    "test.integration.django.apps.app_2",
]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
}
DEBUG = True
ROOT_URLCONF = sys.modules[__name__]
WIREUP = WireupSettings(
    service_modules=[
        "test.shared.shared_services",
        "test.integration.django.service",
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
    path("template_view/foo", TemplateView.as_view(template_name="foo.html")),
    path("template_view/bar", TemplateView.as_view(template_name="bar.html")),
    path("app_1", include("test.integration.django.apps.app_1.urls")),
    path("app_2", include("test.integration.django.apps.app_2.urls")),
]


@pytest.fixture(autouse=True, scope="module")
def django_setup() -> None:
    os.environ["DJANGO_SETTINGS_MODULE"] = (
        "test.integration.django.test_django_integration"
    )
    django.setup()

    # DRF URLs must be added after django.setup() because DRF modules require
    # Django to be configured before they can be imported
    urlpatterns.append(
        path("drf/", include("test.integration.django.apps.drf_app.urls"))
    )


@pytest.fixture
def client() -> Client:
    return Client()


def test_django_thing(client: Client):
    res = client.get("/?name=World")

    assert res.status_code == 200
    assert (
        res.content.decode("utf8")
        == "Hello World! Debug = True. Your lucky number is 4"
    )


def test_get_random(client: Client):
    res = client.get("/classbased?name=Test")

    assert res.status_code == 200
    assert (
        res.content.decode("utf8") == "Hello Test! Debug = True. Your lucky number is 4"
    )


@pytest.mark.parametrize("path", ("foo", "bar"))
def test_get_templated_views(client: Client, path: str):
    res = client.get(f"/template_view/{path}")

    assert res.status_code == 200
    assert res.content.decode("utf8") == path


def test_override(client: Client):
    class RudeGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Bad day to you, {name}"

    with get_app_container().override.service(GreeterService, new=RudeGreeter()):
        res = client.get("/classbased?name=Test")

    assert res.status_code == 200
    assert (
        res.content.decode("utf8")
        == "Bad day to you, Test! Debug = True. Your lucky number is 4"
    )


def test_multiple_apps(client: Client):
    app_1_response = client.get("/app_1/?name=World")

    assert app_1_response.status_code == 200
    assert app_1_response.content.decode("utf8") == "App 1: Hello World"

    app_2_response = client.get("/app_2/?name=World")

    assert app_2_response.status_code == 200
    assert app_2_response.content.decode("utf8") == "App 2: Hello World"


def test_drf_function_based_view(client: Client):
    res = client.get("/drf/fbv/?name=World")

    assert res.status_code == 200
    assert res.json() == {"message": "FBV: Hello World"}


def test_drf_class_based_view(client: Client):
    res = client.get("/drf/cbv/?name=World")

    assert res.status_code == 200
    assert res.json() == {"message": "CBV: Hello World"}


def test_drf_viewset(client: Client):
    res = client.get("/drf/viewset/?name=World")

    assert res.status_code == 200
    assert res.json() == {"message": "ViewSet: Hello World"}


def test_django_fbv_with_inject_decorator(client: Client):
    app_1_response = client.get("/app_1/inject/?name=World")
    app_2_response = client.get("/app_2/inject/?name=World")

    assert app_1_response.status_code == 200
    assert (
        app_1_response.content.decode("utf8")
        == "App 1: Hello World (with inject decorator)"
    )
    assert app_2_response.status_code == 200
    assert (
        app_2_response.content.decode("utf8")
        == "App 2: Hello World (with inject decorator)"
    )


def test_django_cbv_with_inject_decorator(client: Client):
    app_1_response = client.get("/app_1/cbv/inject/?name=World")
    app_2_response = client.get("/app_2/cbv/inject/?name=World")

    assert app_1_response.status_code == 200
    assert (
        app_1_response.content.decode("utf8")
        == "App 1: Hello World (with inject decorator)"
    )
    assert app_2_response.status_code == 200
    assert (
        app_2_response.content.decode("utf8")
        == "App 2: Hello World (with inject decorator)"
    )


def test_inject_decorator_applied_multiple_times():
    with pytest.raises(
        WireupError, match="@inject decorator applied multiple times to"
    ):

        @inject
        @inject
        def _(*__, **___): ...
