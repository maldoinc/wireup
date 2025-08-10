# Starlette Integration

Dependency injection for Starlette is available in the `wireup.integration.starlette` module.

<div class="grid cards annotate" markdown>

-   :material-cog-refresh:{ .lg .middle } __Automatic Dependency Management__

    ---

    Inject dependencies in endpoints and automatically manage container lifecycle.

-   :material-share-circle:{ .lg .middle } __Shared business logic__

    ---

    Wireup is framework-agnostic. Share the service layer between your web application and other interfaces, such as a CLI.
</div>

### Initialize the integration

To initialize the integration, call `wireup.integration.starlette.setup`.

```python
from starlette.applications import Starlette
from starlette.routing import Route
import wireup

app = Starlette()

container = wireup.create_async_container(
    # service_modules is a list of top-level modules with service registrations.
    service_modules=[services],
    # Optionally expose custom parameters to the container.
    parameters={"DEBUG": True}
)

# Initialize the integration.
wireup.integration.starlette.setup(container, app)
```

### Inject in Starlette Endpoints

To inject dependencies decorate endpoints with `@inject` from the `wireup.integration.starlette` module
and annotate parameters as necessary. See [Annotations](../../annotations.md) for more details.

```python title="Starlette Endpoint" hl_lines="3 5 8 14 17"
from starlette.requests import Request
from starlette.responses import JSONResponse
from wireup.integration.starlette import Injected, inject

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

### Accessing the Container

To access the Wireup container directly, use the following functions:

```python
from wireup.integration.starlette import get_app_container, get_request_container

# Access the request-scoped container (used for the current request).
# This is what you almost always want.
# It has all the information the app container has in addition
# to data specific to the current request.
request_container = get_request_container()

# Access the application-wide container (created via `wireup.create_async_container`).
# Use this when you need the container outside of the request context lifecycle.
app_container = get_app_container(app)
```

### Testing

For general testing tips with Wireup refer to the [test docs](../../testing.md). 
With the Starlette integration, you can override dependencies in the container as follows.

```python title="test_thing.py"
from wireup.integration.starlette import get_app_container

def test_override():
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_app_container(app).override.service(GreeterService, new=DummyGreeter()):
        response = client.get("/hello", params={"name": "Test"})
```

See [Starlette integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/starlette/test_starlette_integration.py)
for more examples.

### API Reference

* [starlette_integration](../../class/starlette_integration.md)
