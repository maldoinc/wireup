# Litestar Integration

The `wireup.integration.litestar` module provides dependency injection for Litestar applications.

<div class="grid cards annotate" markdown>

-   :material-cog-refresh:{ .lg .middle } __Automatic Dependency Management__

    ---

    Automatically manage the container lifecycle and inject dependencies into endpoints.

-   :material-share-circle:{ .lg .middle } __Shared Business Logic__

    ---

    Wireup is framework-agnostic, allowing you to share your service layer across web applications and other interfaces, such as CLIs.
</div>

### Setting Up the Integration

To set up the integration, use the `wireup.integration.litestar.setup` function.

```python
from litestar import Litestar
import wireup

app = Litestar([...])  # Your route handlers here

container = wireup.create_async_container(
    # A list of top-level modules containing service registrations.
    service_modules=[services],
    # Optionally, expose custom parameters to the container.
    parameters={"DEBUG": True}
)

# Set up the integration.
wireup.integration.litestar.setup(container, app)
```

### Injecting Dependencies into Endpoints

To inject dependencies, apply the `@inject` decorator from the `wireup.integration.litestar` module to endpoints
and annotate parameters accordingly. Refer to [Annotations](../../annotations.md) for more details.

```python title="Litestar Endpoints" hl_lines="4 7 10 16 19"
from litestar import get
from litestar.websockets import WebSocket
from litestar.response import Response
from wireup.integration.litestar import Injected, inject

@get("/")
@inject
async def index(
    request: Request,
    greeter: Injected[GreeterService],
) -> str:
    return greeter.greet(request.query_params["name"])


@websocket(path="/ws")
@inject
async def websocket_handler(
    socket: WebSocket[Any, Any, State],
    greeter: Injected[GreeterService],
) -> None:
    await socket.accept()
    recv = await socket.receive_json()
    await socket.send_json({"greeting": greeter.greet(recv["name"])})
    await socket.close()
```

### Using Controllers

Litestar also supports class-based controllers. The `@inject` decorator works on controller methods the same way it
works on standalone route handlers. Here's a small example that greets users from a controller method:

```python title="Controller Example"
from litestar import Controller, get
from wireup.integration.litestar import Injected, inject

class UserController(Controller):
    path = "/greet"

    @get()
    @inject
    async def greet(self, greeter: Injected[GreeterService]) -> str:
        return greeter.greet("User")
```

Register controllers the same way you register handlers when constructing the `Litestar` app.


### Inject Litestar Request or WebSocket

To inject the current request/websocket in your services you must add `wireup.integration.litestar` module to your
service modules when creating a container. Here's how you can create request-scoped services that use Litestar's request or websocket:

```python title="Example Services using Litestar Request/WebSocket"
@service(lifetime="scoped")
class RequestContext:
    def __init__(self, request: Request[Any, Any, Any]) -> None:
        self.request = request

    @property
    def name(self) -> str:
        return self.request.query_params["name"]

@service(lifetime="scoped")
class WebSocketContext:
    def __init__(self, socket: WebSocket[Any, Any, Any]) -> None:
        self.socket = socket
```

### Accessing the Container Directly

You can directly access the Wireup container using the following functions:

```python
from wireup.integration.litestar import get_app_container, get_request_container

# Access the request-scoped container (used for the current request).
# This is what you almost always want.
# It has all the information the app container has in addition
# to data specific to the current request.
# You can get an instance of the request container in decorators or other middleware.
request_container = get_request_container()

# Access the application-wide container created with `wireup.create_async_container`.
# Use this for operations outside the request lifecycle.
app_container = get_app_container(app)
```

### Testing

For general testing tips, see the [testing documentation](../../testing.md). To override dependencies in the container during tests, use the following approach:

```python title="test_thing.py"
from wireup.integration.litestar import get_app_container
from litestar.testing import TestClient


class UppercaseGreeter(GreeterService):
    def greet(self, name: str) -> str:
        return super().greet(name).upper()


def test_override(app: Litestar, client: TestClient[Litestar]):
    container = get_app_container(app)

    with container.override.service(GreeterService, new=UppercaseGreeter()):
        response = client.get("/", params={"name": "Test"})

    assert response.text == "HELLO TEST"
    assert response.status_code == 200
```

For more examples, see the [Litestar integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/litestar/test_litestar_integration.py).

### API Reference

* [litestar_integration](../../class/litestar_integration.md)
