import os

import django
import pytest
from django.test import Client
from wireup.integration.django.apps import get_app_container

from test.shared.shared_services.greeter import GreeterService


@pytest.fixture(autouse=True, scope="module")
def django_setup():
    os.environ["DJANGO_SETTINGS_MODULE"] = "test.integration.django_ninja.settings"
    django.setup()


@pytest.fixture
def client():
    return Client()


def test_greet_with_injection(client):
    # GIVEN a Django Ninja endpoint with Injected services
    # WHEN making a request with query parameter
    res = client.get("/greet?name=World")

    # THEN the injected service is used and response is correct
    assert res.status_code == 200
    assert res.json() == {"greeting": "Hello World", "debug": True}


def test_post_with_body_and_injection(client):
    # GIVEN a Django Ninja endpoint with both Body schema and Injected service
    # WHEN making a POST request with JSON body
    res = client.post(
        "/items",
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


def test_multiple_injections(client):
    # GIVEN a Django Ninja endpoint with multiple injectable params
    # WHEN making a request
    res = client.get("/multi-inject")

    # THEN all injections are resolved correctly
    assert res.status_code == 200
    assert res.json() == {
        "greeting": "Hello World",
        "debug": True,
        "has_secret": True,
    }


def test_endpoint_without_injection(client):
    # GIVEN a Django Ninja endpoint without any Wireup injection
    # WHEN making a request
    res = client.get("/no-inject?name=Test")

    # THEN it works normally
    assert res.status_code == 200
    assert res.json() == {"name": "Test"}


def test_override_injected_service(client):
    # GIVEN a custom implementation of GreeterService
    class RudeGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Go away, {name}"

    # WHEN using override context manager
    with get_app_container().override.service(GreeterService, new=RudeGreeter()):
        res = client.get("/greet?name=Bob")

    # THEN the overridden service is used
    assert res.status_code == 200
    assert res.json() == {"greeting": "Go away, Bob", "debug": True}
