Dependency injection for FastAPI is available in the `wireup.integration.fastapi` module.

**Features:**

- [x] Inject dependencies in FastAPI routes.
- [x] Expose `fastapi.Request` as a `scoped` Wireup dependency.
- [x] Close the Wireup container upon application termination for proper resource cleanup.

---

### Initialize the integration

To initialize the integration, call `wireup.integration.fastapi.setup` after adding all routers.

```python
container = wireup.create_async_container(
    # Add service modules.
    service_modules=[
        # Top level module containing service registrations.
        services,
        # Include the integration if you require `fastapi.Request` in Wireup services.
        wireup.integration.fastapi
    ],
    # Expose parameters to Wireup as necessary. 
    parameters={
        "debug": settings.DEBUG
    }
)
wireup.integration.fastapi.setup(container, app)
```

### Inject in HTTP and WebSocket routes

To inject dependencies, add the type to the route's signature and annotate them as necessary.
See [Annotations](../annotations.md) for more details.

=== "HTTP"

    ```python title="HTTP Route"
    @app.get("/random")
    async def target(
        random_service: Injected[RandomService],
        is_debug: Annotated[bool, Inject(param="debug")],

        # This is a regular FastAPI dependency.
        lucky_number: Annotated[int, Depends(get_lucky_number)]
    ): ...
    ```
=== "WebSocket"

    ```python title="WebSocket Route"
    @app.websocket("/ws")
    async def ws(websocket: WebSocket, greeter: Injected[GreeterService]): ...
    ```

!!! tip "Optional Performance Optimization"
    Optimize dependency injection performance by using a custom APIRoute class. 
    This reduces overhead in endpoints that use Wireup injection by avoiding redundant processing.

    ```python
    from fastapi import APIRouter
    from wireup.integration.fastapi import WireupRoute

    router = APIRouter(route_class=WireupRoute)
    ```

    If you already have a custom route class, you can inherit from WireupRoute instead.

    **Under the hood**: FastAPI processes all route parameters, including ones meant for Wireup. 
    The WireupRoute class optimizes this by making Wireup-specific parameters only visible to Wireup, 
    removing unnecessary processing by FastAPI's dependency injection system.

### Inject FastAPI request or websocket

A key feature of the integration is to expose `fastapi.Request` and `fastapi.WebSocket`in Wireup.
To allow injecting these in your services you must add `wireup.integration.fastapi` module to your service modules
when creating a container.

Services depending on it should be transient or scoped, so that these are not shared across requests.

```python
@service(lifetime="scoped")
class HttpAuthenticationService:
    def __init__(self, request: fastapi.Request) -> None: ...


@service(lifetime="scoped")
def example_factory(request: fastapi.Request) -> ExampleService: ...


@service(lifetime="scoped")
class ChatService:
    def __init__(self, websocket: fastapi.WebSocket) -> None:
        await self.websocket.accept()

    async def send(self, data: str):
        await self.websocket.send_text(data)
```

### Accessing the Container

If you ever need to access the Wireup container directly, use the provided functions:

```python
from wireup.integration.fastapi import get_app_container, get_request_container

# Get application-wide container.
app_container: AsyncContainer = get_app_container(app)

# Get request-scoped container.
# This is what is currently injecting services on the active request.
request_container: ScopedAsyncContainer = get_request_container()
```

### Get dependencies in middleware

Wireup integration performs injection only in FastAPI routes. If the container is not stored globally, you can get a reference to it using `get_app_container` and `get_request_container` from the `wireup.integration.fastapi` module.

```python title="example_middleware.py"
from wireup.integration.fastapi import get_request_container

async def example_middleware(request: Request, call_next) -> Response:
    container = get_request_container()
    ...

    return await call_next(request)
```

### Get dependencies in `Depends`.

Similarly, you can get a reference to the container in a FastAPI dependency.

```python
from wireup.integration.fastapi import get_request_container

async def example_dependency(request: Request, other_dependency: Depends(...)):
    container = get_request_container()
    ...
```

!!! warning
    Use `fastapi.Depends` only for specific cases.
    When using Wireup, let it manage all dependencies instead of mixing it with `fastapi.Depends`.

    Note that while this approach works, the reverse does not.
    You cannot require `fastapi.Depends` objects in Wireup services.

### Testing

For general testing tips with Wireup refer to the [test docs](../testing.md). 
With the FastAPI integration, you can override dependencies in the container as follows.

```python title="test_thing.py"
from wireup.integration.fastapi import get_app_container

def test_override(client):
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_app_container(app).override.service(GreeterService, new=DummyGreeter()):
        res = client.get("/greet?name=Test")
```

See [FastAPI integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/test_fastapi_integration.py)
for more examples.

!!! warning
    The Wireup integration relies on FastAPI's lifespan events to close the container upon termination.
    To ensure these events are triggered during testing, instantiate the test client as a context manager.
    This is a requirement due to FastAPI's design, not a limitation of Wireup.

    ```python
    @pytest.fixture()
    def client(app: FastAPI) -> Iterator[TestClient]:
        with TestClient(app) as client:
            yield client
    ```

## API Reference

* [fastapi_integration](../class/fastapi_integration.md)
