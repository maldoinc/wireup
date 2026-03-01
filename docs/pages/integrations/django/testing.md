---
description: Test Django apps with Wireup using Client and AsyncClient, command testing via call_command, and dependency overrides.
---

# Django Testing

Use this page as the canonical reference for testing Wireup in Django projects.

For general testing guidance, also see [Testing](../../testing.md).

## Test `@inject` Request Handlers

Use Django's `Client` for sync views and `AsyncClient` for async views.

```python
from django.test import Client, AsyncClient


def test_sync_view():
    client = Client()
    response = client.get("/greet/?name=World")
    assert response.status_code == 200


async def test_async_view():
    client = AsyncClient()
    response = await client.get("/async-greet/?name=World")
    assert response.status_code == 200
```

## Test `@inject_app` Management Commands

Use `call_command(...)` and capture output with `StringIO`.

```python
from io import StringIO
from django.core.management import call_command


def test_greet_command():
    out = StringIO()
    call_command("greet", "--name=World", stdout=out)
    assert out.getvalue().strip() == "Hello World"
```

## Override Dependencies in Tests

Use app-container overrides for both request and app-level tests.

### Example: Override an injected service for an HTTP endpoint test.

```python
from django.test import Client
from wireup.integration.django import get_app_container

from myapp.services import GreeterService


def test_override_http_endpoint():
    class FakeGreeter:
        def greet(self, name: str) -> str:
            return f"Hi {name}"

    client = Client()
    with get_app_container().override.injectable(
        GreeterService, new=FakeGreeter()
    ):
        response = client.get("/greet/?name=World")

    assert response.status_code == 200
    assert response.content.decode("utf8") == "Hi World"
```

### Example: Override an injected service for a management command test.

```python
from io import StringIO
from django.core.management import call_command
from wireup.integration.django import get_app_container

from myapp.services import GreeterService


def test_override_command():
    class FakeGreeter:
        def greet(self, name: str) -> str:
            return f"Hi {name}"

    out = StringIO()
    with get_app_container().override.injectable(
        GreeterService, new=FakeGreeter()
    ):
        call_command("greet", "--name=World", stdout=out)

    assert out.getvalue().strip() == "Hi World"
```

## DRF and Ninja

DRF and Ninja handlers should use `@inject` explicitly. Their tests follow the same pattern as Django views:

- call endpoint via test client
- assert response
- use `override.injectable(...)` when needed
