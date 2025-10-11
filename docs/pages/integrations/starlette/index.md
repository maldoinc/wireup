# Starlette Integration

The `wireup.integration.starlette` module provides dependency injection for Starlette applications.

<div class="grid cards annotate" markdown>

-   :material-cog-refresh:{ .lg .middle } __Automatic Dependency Management__

    ---

    Automatically manage the container lifecycle and inject dependencies into endpoints.

-   :material-share-circle:{ .lg .middle } __Shared Business Logic__

    ---

    Wireup is framework-agnostic, allowing the service layer to be shared across web applications and other interfaces, such as CLIs.
</div>

### Setting Up the Integration

First, [create an async container](../../container.md#async) with your service modules:

```python
from starlette.applications import Starlette
from starlette.routing import Route
import wireup

app = Starlette()

container = wireup.create_async_container(
    service_modules=[services],
    parameters={"DEBUG": True}  # Optionally expose custom parameters
)
```

Then set up the integration using `wireup.integration.starlette.setup`:

```python
# Set up the integration.
wireup.integration.starlette.setup(container, app)
```

### Injecting Dependencies into Endpoints

To inject dependencies, apply the `@inject` decorator from the `wireup.integration.starlette` module to endpoints
and annotate parameters accordingly. Refer to [Annotations](../../annotations.md) for more details.

```python title="Starlette Endpoint" hl_lines="5 6 8 11 17 20"
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse

from wireup import Injected
from wireup.integration.starlette import inject

@inject
async def get_random(
    request: Request, 
    random: Injected[RandomService],
) -> JSONResponse:
    return JSONResponse({"lucky_number": random.get_random()})


class HelloEndpoint(HTTPEndpoint):
    @inject
    async def get(self,
        request: Request,
        greeter: Injected[GreeterService]
    ) -> PlainTextResponse:
        greeting = greeter.greet(request.query_params.get("name", "World"))

        return PlainTextResponse(greeting)
```

### Inject Starlette request or WebSocket

To inject the current request/websocket in services, include the `wireup.integration.starlette` module
in the service modules when [creating the container](../../container.md).

```python
container = wireup.create_async_container(
    service_modules=[..., wireup.integration.starlette],
)
```

### Using Starlette Request

```python title="Example Service using Starlette Request"
@service(lifetime="scoped")
class RequestContext:
    def __init__(self, request: Request):
        self.request = request

    @property
    def name(self) -> str:
        return self.request.query_params.get("name", "World")
```

### Accessing the Container Directly

You can directly access the Wireup container using the following functions:

```python
from wireup.integration.starlette import get_app_container, get_request_container

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
from wireup.integration.starlette import get_app_container


class UppercaseGreeter(GreeterService):
    def greet(self, name: str) -> str:
        return super().greet(name).upper()


def test_override():
    container = get_app_container(app)

    with container.override.service(GreeterService, new=UppercaseGreeter()):
        response = client.get("/hello", params={"name": "world"})

    assert response.text == "HELLO WORLD"
```

For more examples, see the [Starlette integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/starlette/test_starlette_integration.py).

### API Reference

* [starlette_integration](../../class/starlette_integration.md)
