Dependency injection for FastAPI is available in the `wireup.integration.fastapi_integration` module.

**Features:**

- [x] Inject dependencies in FastAPI routes.
- [x] Expose `fastapi.Request` as a wireup dependency.
    * Available as a `scoped` dependency, your services can ask for a fastapi request object.
- [x] Close the Wireup container when application terminates to perform proper cleanup of resources.
    * Calls `await container.close()` right before shutdown.


## Guide

### Initialize the integration

To Initialize the integration you must call `wireup.integration.fastapi.setup` once all routers have been added.

```python
container = wireup.create_async_container(
    # Add service modules.
    service_modules=[services],
    # Expose parameters to Wireup as necessary. 
    parameters={
        "debug": settings.DEBUG
    }
)
wireup.integration.fastapi.setup(container, app)
```


### Inject in HTTP and WebSocket routes

To inject simply add to the route's signature the type to inject. Due to FastAPI design it MUST be annotated with
`Inject()` as shown.


=== "HTTP"

    ```python title="main.py"
    app = FastAPI()

    @app.get("/random")
    async def target(
        # Inject annotation tells wireup that this argument should be injected.
        # Inject() annotation is required otherwise fastapi will think it's a pydantic model.
        random_service: Annotated[RandomService, Inject()],
        is_debug: Annotated[bool, Inject(param="debug")],

        # This is a regular FastAPI dependency.
        lucky_number: Annotated[int, Depends(get_lucky_number)]
    ): ...
    ```
=== "WebSocket"

    ```python
    @app.websocket("/ws")
    async def ws(websocket: WebSocket, greeter: Annotated[GreeterService, Inject()]): ...
    ```

### Get dependencies in middleware

Wireup integration performs injection only in fastapi routes. If you're not storing the container in a global variable, 
you can always get a reference to it wherever you have a fastapi application reference
by using `wireup.integration.fastapi.get_container`.

```python title="example_middleware.py"
from wireup.integration.fastapi import get_container

async def example_middleware(request: Request, call_next) -> Response:
    container = get_container(request.app)
    ...

    return await call_next(request)
```


### Get dependencies in `Depends`.

In the same way as above, you can get a reference to it in a fastapi dependency.

```python
from wireup.integration.fastapi import get_container

async def example_dependency(request: Request, other_dependency: Depends(...)):
    container = get_container(request.app)
    ...
```

!!! warning
    Use `fastapi.Depends` only for specific cases.
    When using Wireup, let it manage all dependencies instead of mixing it with `fastapi.Depends`.

    Note that while this approach works, the reverse does not.
    You cannot require `fastapi.Depends` objects in Wireup services.

### Inject FastAPI request

A key feature of the integration is to expose `fastapi.Request` in wireup.

Services depending on it should be transient or scoped, so that these are not shared across requests.

```python
@service(lifetime="scoped")
class HttpAuthenticationService:
    def __init__(self, request: fastapi.Request) -> None: ...


@service(lifetime="scoped")
def example_factory(request: fastapi.Request) -> ExampleService: ...
```

### Testing

For general testing tips with Wireup refer to the [test docs](../testing.md). 
With the FastAPI integration you can override dependencies in the container as follows.

```python title="test_thing.py"
from wireup.integration.fastapi import get_container

def test_override(client):
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_container(app).override.service(GreeterService, new=DummyGreeter()):
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

## Api Reference

* [fastapi_integration](../class/fastapi_integration.md)
