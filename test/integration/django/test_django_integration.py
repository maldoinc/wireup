import os
import sys
from pathlib import Path
from unittest.mock import patch

import django
import pytest
from django.apps import apps
from django.test import AsyncClient, Client
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

    # DRF and Django Ninja URLs must be added after django.setup() because these modules
    # require Django to be configured before they can be imported
    urlpatterns.append(path("drf/", include("test.integration.django.apps.drf_app.urls")))
    urlpatterns.append(path("ninja/", include("test.integration.django.apps.ninja_app.urls")))


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

    with get_app_container().override.service(GreeterService, new=RudeGreeter()):
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
    # GIVEN an async Django view with an injected async service
    # WHEN making a request
    res = await async_client.get("/async_greet?name=World")

    # THEN the async service is properly injected and works
    assert res.status_code == 200
    assert res.content.decode("utf8") == "Hello World! Debug = True"


async def test_async_cbv_with_async_service(async_client: AsyncClient):
    # GIVEN an async Django CBV with an injected async service
    # WHEN making a request
    res = await async_client.get("/async_classbased?name=World")

    # THEN the async service is properly injected and works
    assert res.status_code == 200
    assert res.content.decode("utf8") == "Hello World! Debug = True. Your lucky number is 4"


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
    # This test verifies that function-based views with @inject decorator
    # skip auto-injection (avoiding double injection)
    app_1_response = client.get("/app_1/inject/?name=World")
    app_2_response = client.get("/app_2/inject/?name=World")

    assert app_1_response.status_code == 200
    assert app_1_response.content.decode("utf8") == "App 1: Hello World (with inject decorator)"
    assert app_2_response.status_code == 200
    assert app_2_response.content.decode("utf8") == "App 2: Hello World (with inject decorator)"


def test_django_cbv_with_inject_decorator(client: Client):
    # This test verifies that class-based views with @inject decorator on methods
    # skip auto-injection for those methods (avoiding double injection)
    app_1_response = client.get("/app_1/cbv/inject/?name=World")
    app_2_response = client.get("/app_2/cbv/inject/?name=World")

    assert app_1_response.status_code == 200
    assert app_1_response.content.decode("utf8") == "App 1: Hello World (with inject decorator)"
    assert app_2_response.status_code == 200
    assert app_2_response.content.decode("utf8") == "App 2: Hello World (with inject decorator)"


def test_auto_inject_views_setting_default():
    # GIVEN WireupSettings with default values
    settings_default = WireupSettings(service_modules=["test.shared.shared_services"])

    # THEN auto_inject_views should default to True
    assert settings_default.auto_inject_views is True


def test_auto_inject_views_disabled_skips_injection():
    # GIVEN WireupSettings with auto_inject_views=False
    settings_disabled = WireupSettings(
        service_modules=["test.shared.shared_services"],
        auto_inject_views=False,
    )

    # WHEN we call ready() with auto_inject_views=False
    wireup_config = apps.get_app_config("wireup")

    with (
        patch("wireup.integration.django.apps.settings") as mock_settings,
        patch.object(wireup_config, "_inject") as mock_inject,
    ):
        mock_settings.WIREUP = settings_disabled

        wireup_config.ready()

        # THEN _inject should NOT be called
        mock_inject.assert_not_called()


def test_auto_inject_views_enabled_calls_injection():
    # GIVEN WireupSettings with auto_inject_views=True (default)
    settings_enabled = WireupSettings(
        service_modules=["test.shared.shared_services"],
        auto_inject_views=True,
    )

    # WHEN we call ready() with auto_inject_views=True
    wireup_config = apps.get_app_config("wireup")

    with patch("wireup.integration.django.apps.settings") as mock_settings, patch.object(
        wireup_config, "_inject"
    ) as mock_inject:
        mock_settings.WIREUP = settings_enabled

        wireup_config.ready()

        # THEN _inject should be called
        mock_inject.assert_called_once()


def test_inject_decorator_applied_multiple_times():
    with pytest.raises(WireupError, match="@inject decorator applied multiple times to"):

        @inject
        @inject
        def _(*__, **___): ...


# Django Ninja tests


def test_ninja_greet_with_injection(client: Client):
    # GIVEN a Django Ninja endpoint with Injected services
    # WHEN making a request with query parameter
    res = client.get("/ninja/greet?name=World")

    # THEN the injected service is used and response is correct
    assert res.status_code == 200
    assert res.json() == {"greeting": "Hello World"}


def test_ninja_post_with_body_and_injection(client: Client):
    # GIVEN a Django Ninja endpoint with both Body schema and Injected service
    # WHEN making a POST request with JSON body
    res = client.post(
        "/ninja/items",
        data={"name": "Widget", "price": 9.99},
        content_type="application/json",
    )

    # THEN both the body is parsed and the injected service works
    assert res.status_code == 200
    assert res.json() == {
        "id": 1,
        "name": "Widget",
        "price": 9.99,
        "message": "Hello Widget",
    }


def test_ninja_endpoint_without_injection(client: Client):
    # GIVEN a Django Ninja endpoint without any Wireup injection
    # WHEN making a request
    res = client.get("/ninja/no-inject?name=Test")

    # THEN it works normally
    assert res.status_code == 200
    assert res.json() == {"name": "Test"}


def test_ninja_override_injected_service(client: Client):
    # GIVEN a custom implementation of GreeterService
    class RudeGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Go away, {name}"

    # WHEN using override context manager
    with get_app_container().override.service(GreeterService, new=RudeGreeter()):
        res = client.get("/ninja/greet?name=Bob")

    # THEN the overridden service is used
    assert res.status_code == 200
    assert res.json() == {"greeting": "Go away, Bob"}


# Django Ninja async tests


async def test_ninja_async_greet_with_injection(async_client: AsyncClient):
    # GIVEN an async Django Ninja endpoint with Injected async service
    # WHEN making a request with query parameter
    res = await async_client.get("/ninja/async-greet?name=World")

    # THEN the async injected service is used and response is correct
    assert res.status_code == 200
    assert res.json() == {"greeting": "Hello World"}


async def test_ninja_async_post_with_body_and_injection(async_client: AsyncClient):
    # GIVEN an async Django Ninja endpoint with both Body schema and Injected async service
    # WHEN making a POST request with JSON body
    res = await async_client.post(
        "/ninja/async-items",
        data={"name": "Widget", "price": 9.99},
        content_type="application/json",
    )

    # THEN both the body is parsed and the async injected service works
    assert res.status_code == 200
    assert res.json() == {
        "id": 1,
        "name": "Widget",
        "price": 9.99,
        "message": "Hello Widget",
    }
