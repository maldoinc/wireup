---
description: Test FastAPI apps with Wireup using TestClient, dependency overrides, and class-based handler startup-safe mocking.
---

# FastAPI Testing

Use this page as the FastAPI-specific testing guide for Wireup.

For general testing guidance, see [Testing](../../testing.md).

## Basic Endpoint Testing

Use `TestClient` as a context manager so FastAPI lifespan runs.

```python
from fastapi.testclient import TestClient


def test_endpoint(app: FastAPI):
    with TestClient(app) as client:
        response = client.get("/greet?name=World")
        assert response.status_code == 200
```

## Override Dependencies in Tests

Use app-container overrides to inject fakes or mocks.

```python
from fastapi.testclient import TestClient
from wireup.integration.fastapi import get_app_container


def test_override(app: FastAPI):
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_app_container(app).override.injectable(
        GreeterService, new=DummyGreeter()
    ):
        with TestClient(app) as client:
            response = client.get("/greet?name=Test")

    assert response.status_code == 200
```

## Testing Request-Lifecycle Injection

If tests depend on request-time injection (middleware/decorators using `@inject` or `get_request_container()`), enable
`middleware_mode=True` and run with `TestClient` context manager.

```python
wireup.integration.fastapi.setup(container, app, middleware_mode=True)

with TestClient(app) as client:
    response = client.get("/requires-request-id")
```

## Setup Timing in Tests

Best practice is to call `setup(...)` after routes are added. If setup is called earlier, lifespan must run before
handling requests (again, use `TestClient` as a context manager).

## Class-Based Handlers

Class-based handlers resolve constructor dependencies at startup. Apply overrides before creating `TestClient`.

```python
import contextlib
from collections.abc import Iterator
from fastapi import FastAPI
from fastapi.testclient import TestClient
import wireup
import wireup.integration.fastapi
from wireup import InjectableOverride
from wireup.integration.fastapi import get_app_container


@contextlib.contextmanager
def create_test_app(
    overrides: list[InjectableOverride] | None = None,
) -> Iterator[FastAPI]:
    app = create_app()  # Create app, add routes, setup Wireup.

    with get_app_container(app).override.injectables(overrides or []):
        yield app


def test_user_handler_with_override():
    overrides = [
        InjectableOverride(target=UserProfileService, new=MockUserService())
    ]

    # Override first, then start app lifecycle.
    with create_test_app(overrides=overrides) as app:
        with TestClient(app) as client:
            response = client.get("/users/")

    assert response.status_code == 200
```

See [Class-Based Handlers](class_based_handlers.md#testing) for more details.

## Background Tasks

For task injection and testing, see [Background Tasks](background_tasks.md).

## Common Test Failures

- Injection not set up: verify `wireup.integration.fastapi.setup(container, app)` was called.
- Request container unavailable: verify `middleware_mode=True` for request-time middleware/decorator code.
- Lifespan not running: verify `with TestClient(app) as client:` usage.

For runtime/setup issues beyond tests, see [Troubleshooting](troubleshooting.md).
