---
description: Test code that uses Wireup by reusing your production wiring entry point, exposing the app container through pytest fixtures, and applying overrides deliberately.
---

# Testing

Wireup does not require a special testing style. If a test does not need the container, instantiate the class
yourself. When a test needs the real dependency graph, reuse the same production entry point, expose the app
container through pytest fixtures, and apply overrides there.


## Reuse Production Wiring in Tests

When a test needs the real Wireup graph, start from the same entry point used by production code.

This keeps registrations, configuration, scopes, and integration setup in one place.

## Pytest Fixtures

For web apps, this is often a `create_app()` function. Build a fresh app fixture from that entry point, derive the
Wireup container from it, and expose a test client fixture from the same app. After that, `container` can be used like
any other pytest fixture by listing it in a test function signature.

```python title="app.py"
from fastapi import FastAPI
import wireup
import wireup.integration.fastapi
from wireup import Injected, injectable


@injectable
class GreeterService:
    def greet(self, name: str) -> str:
        return f"Hello, {name}"


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/greet")
    async def greet(
        name: str, greeter: Injected[GreeterService]
    ) -> dict[str, str]:
        return {"message": greeter.greet(name)}

    container = wireup.create_async_container(injectables=[GreeterService])
    wireup.integration.fastapi.setup(container, app)

    return app
```

```python title="conftest.py"
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from wireup.integration.fastapi import get_app_container

from myapp.app import create_app


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def container(app: FastAPI):
    return get_app_container(app)


@pytest.fixture
def client(app: FastAPI):
    with TestClient(app) as client:
        yield client
```

```python title="test_app.py"
from fastapi.testclient import TestClient

from myapp.app import GreeterService


def test_greet(client: TestClient) -> None:
    response = client.get("/greet", params={"name": "World"})

    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World"}


class TestGreeter(GreeterService):
    def greet(self, name: str) -> str:
        return f"Hi, {name}"


def test_greet_with_override(container, client: TestClient) -> None:
    with container.override.injectable(GreeterService, new=TestGreeter()):
        response = client.get("/greet", params={"name": "World"})

    assert response.status_code == 200
    assert response.json() == {"message": "Hi, World"}
```

## Resolve Real Services from the Fixture

Once you have a `container` fixture built from your production wiring entry point, tests can resolve the same services
the application would resolve at runtime.

```python
import pytest


async def test_user_service(container) -> None:
    user_service = await container.get(UserService)

    assert user_service.get_user_name(1) == "Test User"
```

### `scoped` and `transient` services

The root container only resolves singletons. If the service under test is `scoped` or `transient`, open a scope first.

```python
import pytest


async def test_request_service(container) -> None:
    async with container.enter_scope() as scope:
        request_service = await scope.get(RequestService)
```

See [Lifetimes & Scopes](lifetimes_and_scopes.md) for the lifetime rules behind this.

## Override Dependencies

Use overrides when the app/container should stay real, but one dependency should be replaced for the test.
If you want to choose different registrations before the container is created, see
[Conditional Registration](conditional_registration.md).

Overrides only affect future injection requests. Already-created singleton or scoped objects are not rebuilt when one
of their dependencies is overridden. If singleton `A` depends on `B` and `A` was already created, overriding `B` does
not rebuild `A`; calling `get(A)` again returns the existing `A`, still holding the original `B`. The same rule
applies to objects already created in the current scope.

Apply overrides before the first resolution of the object you want to affect. If your integration resolves objects at
startup, apply overrides before creating the test client or starting the app.

When using `as_type`, override the `as_type` target, not the concrete implementation. When overriding a qualified
dependency, include the qualifier in the override target.

### Override One Dependency

```python
import pytest
from unittest.mock import MagicMock


async def test_notification_service(container) -> None:
    fake_email_client = MagicMock(spec=EmailClient)

    with container.override.injectable(EmailClient, new=fake_email_client):
        notifier = await container.get(NotificationService)
        notifier.send_welcome_email("alice@example.com")

    fake_email_client.send.assert_called_once()
```

### Override Multiple Dependencies

When several injected dependencies should be replaced together, use `container.override.injectables(...)`.

```python
import pytest
from unittest.mock import MagicMock
from wireup import InjectableOverride


async def test_checkout(container) -> None:
    user_service_mock = MagicMock()
    order_service_mock = MagicMock()

    overrides = [
        InjectableOverride(target=UserService, new=user_service_mock),
        InjectableOverride(target=OrderService, new=order_service_mock),
    ]

    with container.override.injectables(overrides=overrides):
        checkout_service = await container.get(CheckoutService)
```

## Global Overrides with Fixtures

If many tests need the same auth or user setup, put those Wireup overrides in a fixture instead of repeating them in
every test.

```python title="conftest.py"
import pytest
from wireup.integration.fastapi import get_app_container

from myapp.app import create_app
from myapp.auth import AuthenticatedUser, AuthService


class AllowAllAuth(AuthService):
    def require_user(self) -> AuthenticatedUser:
        return AuthenticatedUser(id="test-user", is_admin=True)


@pytest.fixture
def app(request):
    app = create_app()
    overrides = getattr(request, "param", [])

    if not overrides:
        yield app
        return

    container = get_app_container(app)
    with container.override.injectables(overrides=overrides):
        yield app
```

```python title="test_admin.py"
import pytest
from wireup import InjectableOverride

from myapp.auth import AllowAllAuth, AuthenticatedUser, AuthService


@pytest.mark.parametrize(
    "app",
    [
        [
            InjectableOverride(target=AuthService, new=AllowAllAuth()),
            InjectableOverride(
                target=AuthenticatedUser,
                new=AuthenticatedUser(id="test-user", is_admin=True),
            ),
        ]
    ],
    indirect=True,
)
def test_admin_dashboard(client) -> None:
    response = client.get("/admin")

    assert response.status_code == 200
```

If most tests in a module need the same setup, you can apply the same override list from a shared fixture instead of
repeating it in every test.

## Next Steps

- [Container](container.md) - Learn about the container API.
- [Lifetimes & Scopes](lifetimes_and_scopes.md) - Understand how scopes affect testing.
- [FastAPI Testing](integrations/fastapi/testing.md) - FastAPI-specific testing guidance.
