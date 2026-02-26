# :simple-fastapi: FastAPI Integration

<div class="grid cards annotate" markdown>

- :material-needle:{ .lg .middle } __Clean Injection__

    ______________________________________________________________________

    Declare dependencies by using type annotations. No `Depends()` chains required.

- :material-speedometer:{ .lg .middle } __Zero Runtime Overhead__

    ______________________________________________________________________

    Inject dependencies with **zero** runtime overhead using Class-Based Handlers.

    [:octicons-arrow-right-24: Learn more](class_based_handlers.md)

- :octicons-package-dependents-24:{ .lg .middle } __Access Anywhere__

    ______________________________________________________________________

    Retrieve the container in middleware, decorators, and other places where FastAPI's DI can't reach.

    [:octicons-arrow-right-24: Learn more](request_lifecycle_patterns.md)

- :material-share-circle:{ .lg .middle } __Framework-Agnostic__

    ______________________________________________________________________

    Share your service layer with CLI tools, background workers, and other frameworks.

</div>

## Quick Start

Here is a complete, copy-pasteable example to get you running in under 2 minutes.

Create an [async container](../../container.md), define your services, then initialize the integration by calling
`wireup.integration.fastapi.setup` **after adding all routers**:

```python title="main.py"
import wireup
from fastapi import FastAPI
from wireup import injectable, Injected
import wireup.integration.fastapi


# 1. Define a service (add @injectable)
@injectable
class GreeterService:
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"


# 2. Create the container
container = wireup.create_async_container(injectables=[GreeterService])

# 3. Create the FastAPI app and define your routes
app = FastAPI()


@app.get("/")
async def greet(greeter: Injected[GreeterService]):
    return {"message": greeter.greet("World")}


# 4. Initialize Wireup (after all routes are added)
wireup.integration.fastapi.setup(container, app)
```

Run the server with:

```bash
fastapi dev main.py
```

??? example "See how Wireup compares to `Depends()`"

    This comparison shows the boilerplate reduction when using Wireup's type-based injection versus `Depends()` chains.

    === "Before (Standard FastAPI)"

        ```python
        # Define your services
        class UserRepository:
            def __init__(self, db: Database) -> None:
                self.db = db


        class UserService:
            def __init__(self, repo: UserRepository) -> None:
                self.repo = repo


        # Create factory functions for each dependency
        def get_db() -> Database: ...


        def get_user_repo(db: Annotated[Database, Depends(get_db)]) -> UserRepository:
            return UserRepository(db)


        def get_user_service(
            repo: Annotated[UserRepository, Depends(get_user_repo)],
        ) -> UserService:
            return UserService(repo)


        # Wire up the dependency chain in the route
        @app.get("/users")
        async def list_users(
            service: Annotated[UserService, Depends(get_user_service)],
        ):
            return service.find_all()
        ```

    === "After (Wireup)"

        ```python
        # Add @injectable
        @injectable
        class UserRepository:
            def __init__(self, db: Database) -> None:
                self.db = db


        @injectable
        class UserService:
            def __init__(self, repo: UserRepository) -> None:
                self.repo = repo


        # Inject directly by type
        @app.get("/users")
        async def list_users(service: Injected[UserService]):
            return service.find_all()
        ```

## Features

### HTTP and WebSocket Injection

Inject dependencies in HTTP routes and WebSockets.

=== "HTTP Route"

    ```python
    from typing import Annotated
    from fastapi import Depends
    from wireup import Injected, Inject


    @app.get("/random")
    async def target(
        # Inject custom services
        random_service: Injected[RandomService],
        # Inject configuration values
        is_debug: Annotated[bool, Inject(config="debug")],
        # You can still use regular FastAPI dependencies alongside Wireup
        user_agent: Annotated[str | None, Header()] = None,
    ): ...
    ```

=== "WebSocket Route"

    ```python
    from fastapi import WebSocket
    from wireup import Injected


    @app.websocket("/ws")
    async def ws(websocket: WebSocket, greeter: Injected[GreeterService]): ...
    ```

### Class-Based Handlers (Zero Overhead)

For the best performance and organization, use **Class-Based Handlers**. Dependencies injected into the constructor are
resolved **only once** at startup, removing the overhead of dependency resolution from the request cycle entirely.

```python
class UserHandler:
    router = fastapi.APIRouter()

    # Injected ONCE at startup (Zero runtime cost)
    def __init__(self, user_service: UserProfileService) -> None:
        self.user_service = user_service

    @router.get("/")
    async def list_all(self):
        return self.user_service.find_all()
```

[:octicons-arrow-right-24: Read the Class-Based Handlers guide](class_based_handlers.md) (similar to `@cbv` from
`fastapi-utils`, but with zero per-request overhead)

!!! tip "Performance Tip: Use WireupRoute"

    Improve performance in **function-based routes** by using a custom `APIRoute` class. This reduces overhead in endpoints
    that use Wireup injection by avoiding redundant processing.

    ```python
    from fastapi import APIRouter
    from wireup.integration.fastapi import WireupRoute

    router = APIRouter(route_class=WireupRoute)
    ```

    **Under the hood**: FastAPI processes all route parameters, including ones meant for Wireup. The `WireupRoute` class
    optimizes this by making Wireup-specific parameters only visible to Wireup, removing unnecessary processing by FastAPI's
    dependency injection system.

### Injecting Request & WebSocket

To inject the `Request` or `WebSocket` object into your scoped-lifetime services (e.g. for logging or auth), add
`wireup.integration.fastapi` to your container and request `fastapi.Request` or `fastapi.WebSocket` in your
dependencies.

```python hl_lines="6"
import wireup
import wireup.integration.fastapi

container = wireup.create_async_container(
    # Add the integration module to injectables
    injectables=[services, wireup.integration.fastapi],
)
```

```python hl_lines="6"
import fastapi


@injectable(lifetime="scoped")
class HttpAuthenticationService:
    def __init__(self, request: fastapi.Request) -> None: ...
```

## Testing

For general testing tips with Wireup refer to the [test docs](../../testing.md). With the FastAPI integration, you can
override dependencies in the container as follows.

```python title="test_thing.py"
from wireup.integration.fastapi import get_app_container


def test_override(client):
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_app_container(app).override.injectable(
        GreeterService,
        new=DummyGreeter(),
    ):
        res = client.get("/greet?name=Test")
```

??? example "Pitfall: Why `lru_cache` leaks state in tests"

    In standard FastAPI applications, singletons are often implemented using `@lru_cache`. This can cause state to leak
    between tests because the cache persists globally in memory.

    ```python
    # Standard FastAPI
    @lru_cache
    def get_settings():
        return Settings()


    def test_one():
        # Modifies the cached settings instance
        get_settings().debug = True


    def test_two():
        # FAILS: This test inherits the modified state from test_one!
        assert get_settings().debug is False
    ```

    **Wireup avoids this automatically.**

    When you create a fresh container/app for each test (via a pytest fixture), Wireup creates fresh instances of all your
    services. There is no global cache to clear.

See
[FastAPI integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/fastapi/test_fastapi_integration.py)
for more examples.

!!! warning

    FastAPI's lifespan events are required to close the Wireup container properly. Use a context manager when instantiating
    the test client if using class-based handlers or generator factories in the application.

    ```python
    @pytest.fixture()
    def client(app: FastAPI) -> Iterator[TestClient]:
        with TestClient(app) as client:
            yield client
    ```

[:octicons-arrow-right-24: Read the full Testing guide](../../testing.md)

## API Reference

- [fastapi_integration](../../class/fastapi_integration.md)
