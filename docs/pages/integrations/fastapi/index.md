# :simple-fastapi: FastAPI Integration

<div class="grid cards annotate" markdown>

-   :material-speedometer:{ .lg .middle } __Zero Runtime Overhead__

    ---

    Inject dependencies with __zero__ runtime overhead using Class-Based Handlers.

    [:octicons-arrow-right-24: Learn more](class_based_handlers.md)


-   :material-cog-refresh:{ .lg .middle } __Automatic Dependency Management__

    ---

    Inject dependencies in routes and automatically manage container lifecycle.



-   :octicons-package-dependents-24:{ .lg .middle } __Global Access__

    ---

    Retrieve dependencies in middleware and route handler decorators where they are normally unavailable in FastAPI.

    [:octicons-arrow-right-24: Learn more](direct_container_access.md)

-   :material-share-circle:{ .lg .middle } __Shared business logic__

    ---

    Wireup is framework-agnostic. Use it to share the service layer between web applications and other interfaces, such as a CLI.
</div>

### Getting started

First, [create an async container](../../container.md)

```python
import wireup
from myapp import services

container = wireup.create_async_container(
    service_modules=[services],
    config={"debug": settings.DEBUG},
)
```

Then initialize the integration by calling `wireup.integration.fastapi.setup` after adding all routers:

```python
from fastapi import FastAPI

app = FastAPI()

# Add routers here
# app.include_router(...)

wireup.integration.fastapi.setup(
    container, 
    app, 
    class_based_handlers=[...]  # Include Wireup Class-Based Handlers
)
```

### Inject in HTTP and WebSocket routes

To inject dependencies, add the type to the route's signature and annotate them as necessary.
See [Annotations](../../annotations.md) for more details.

=== "HTTP"

    ```python title="HTTP Route"
    from typing import Annotated
    from fastapi import Depends
    from wireup import Injected, Inject

    @app.get("/random")
    async def target(
        random_service: Injected[RandomService],
        is_debug: Annotated[bool, Inject(config="debug")],

        # This is a regular FastAPI dependency.
        lucky_number: Annotated[int, Depends(get_lucky_number)]
    ): ...
    ```
=== "WebSocket"

    ```python title="WebSocket Route"
    from fastapi import WebSocket
    from wireup import Injected

    @app.websocket("/ws")
    async def ws(websocket: WebSocket, greeter: Injected[GreeterService]): ...
    ```

!!! tip
    Improve performance by using a custom APIRoute class. 
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

To inject the current request/websocket in services, include `wireup.integration.fastapi` 
module in the service modules when creating the container.

```python
import wireup

container = wireup.create_async_container(
    service_modules=[services, wireup.integration.fastapi],
    config={"debug": settings.DEBUG},
)
```

#### Use Request and WebSocket

```python
import fastapi
from wireup import service

@service(lifetime="scoped")
class HttpAuthenticationService:
    def __init__(self, request: fastapi.Request) -> None: ...
```

```python
import fastapi
from wireup import service

@service(lifetime="scoped")
class ChatService:
    def __init__(self, websocket: fastapi.WebSocket) -> None:
        await self.websocket.accept()

    async def send(self, data: str):
        await self.websocket.send_text(data)
```


### Testing

For general testing tips with Wireup refer to the [test docs](../../testing.md). 
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
    FastAPI's lifespan events are required to close the Wireup container properly. 
    Use a context manager when instantiating the test client if using class-based handlers or generator factories in the application.

    ```python
    @pytest.fixture()
    def client(app: FastAPI) -> Iterator[TestClient]:
        with TestClient(app) as client:
            yield client
    ```

### API Reference

* [fastapi_integration](../../class/fastapi_integration.md)
