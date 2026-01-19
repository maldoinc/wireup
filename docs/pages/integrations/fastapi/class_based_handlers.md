Wireup provides native support for Class-Based Handlers (also known as Controllers or Class-Based Views). This allows
you to group related endpoints into a single class, sharing dependencies and logic.

!!! tip "Coming from `fastapi-utils`?"

    This is Wireup's equivalent to `@cbv` but with true zero-overhead constructor injection.

## Zero-Overhead

With standard FastAPI `Depends()`, dependencies are resolved on **every request**. Even for singletons (typically
implemented via `@lru_cache`), FastAPI invokes its dependency injection mechanism to retrieve the same cached value.

With Wireup's Class-Based Handlers, constructor dependencies are resolved **exactly once** when the application starts.
This removes dependency resolution from the request cycle entirely, resulting in zero per-request overhead.

### When to use what?

| Injection Type               | Lifecycle       | Performance Cost     | Best For                                                   |
| ---------------------------- | --------------- | -------------------- | ---------------------------------------------------------- |
| **Constructor** (`__init__`) | **Startup**     | **Zero** (Paid once) | Singletons, Configuration, API Clients, Stateless Services |
| **Method** (`Injected[...]`) | **Per Request** | Low (Normal DI cost) | User Context, Database Sessions, Request-Scoped Data       |

## Usage Guide

### 1. Define the Handler

Create a class with a `router` attribute. Use `WireupRoute` to enable method injection.

```python title="controllers/user_controller.py"
import fastapi
from wireup import Injected
from wireup.integration.fastapi import WireupRoute


class UserHandler:
    # 1. Define a router. Use WireupRoute to enable injection in methods.
    router = fastapi.APIRouter(
        prefix="/users", tags=["Users"], route_class=WireupRoute
    )

    # 2. Inject Singletons/Config here (Zero Overhead)
    def __init__(
        self, user_service: UserProfileService, db_pool: DbPool
    ) -> None:
        self.user_service = user_service
        self.db_pool = db_pool

    # 3. Standard FastAPI decorators work as expected
    @router.get("/")
    async def list_users(self):
        # reuse self.user_service without re-injection
        return self.user_service.find_all()

    # 4. Inject Request-Scoped dependencies in methods
    @router.get("/me")
    async def get_profile(
        self,
        # This is injected fresh for every request
        auth: Injected[AuthenticationService],
    ) -> fastapi.Response:
        return self.user_service.get_profile(auth.current_user)
```

!!! note "Why the different injection syntax?"

    The handler class is instantiated by Wireup (like any `@injectable`), so constructor parameters use plain type hints.
    Route methods are called by FastAPI, so any additional dependencies need `Injected[T]` to distinguish them from regular
    FastAPI parameters like `Query`, `Path`, etc.

### 2. Register the Handler

Pass your handler classes to `wireup.integration.fastapi.setup`. **Do not** include the router in the FastAPI app
manually; Wireup handles this for you.

```python title="main.py"
wireup.integration.fastapi.setup(
    container,
    app,
    class_based_handlers=[
        UserHandler,
        OrderHandler,
        ProductHandler,
    ],
)
```

## Testing

Class-Based Handlers are initialized during the FastAPI **Lifespan** (startup event). When testing, you must ensure the
lifecycle events are triggered.

The easiest way is to use `TestClient` as a context manager.

```python title="conftest.py"
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(app: FastAPI):
    # This triggers startup/shutdown events, initializing your handlers
    with TestClient(app) as client:
        yield client
```

### Overriding Dependencies

To test with overridden dependencies (mocks, stubs, fakes, etc.), set up the override before creating the `TestClient`.

```python
from wireup.integration.fastapi import get_app_container


def test_user_handler(app):
    with get_app_container(app).override.injectable(
        UserProfileService, new=MockUserService()
    ):
        # Start the client INSIDE the override block
        # The handler is initialized with the mock during startup
        with TestClient(app) as client:
            client.get("/users/")
```

!!! tip "Performance Tip"

    If you have high-traffic endpoints, moving dependencies from `Injected[...]` (method) to `__init__` (constructor) can
    measurably improve latency by skipping the dependency resolution step entirely for those requests.

## Next Steps

- [FastAPI Integration](index.md) - Full integration overview.
- [Lifetimes & Scopes](../../lifetimes_and_scopes.md) - Understand when to use singletons vs scoped dependencies.
