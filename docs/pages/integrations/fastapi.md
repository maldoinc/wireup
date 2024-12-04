Dependency injection for FastAPI is available in the `wireup.integration.fastapi_integration` module.

**Features:**

- [x] Inject dependencies in FastAPI routes.
    * Eliminates the need for `@container.autowire`.
- [x] Expose `fastapi.Request` as a wireup dependency.
    * Available as a `TRANSIENT` scoped dependency, your services can ask for a fastapi request object.
- [x] Can: Mix Wireup and FastAPI dependencies in routes.
- [x] Can: Use Wireup in FastAPI dependencies.
- [ ] Cannot: Use FastAPI dependencies in Wireup service objects.

## Getting Started

```python title="main.py"
app = FastAPI()

@app.get("/random")
async def target(
    # Inject annotation tells wireup that this argument should be injected.
    # Inject() annotation is required otherwise fastapi will think it's a pydantic model.
    random_service: Annotated[RandomService, Inject()],
    is_debug: Annotated[bool, Inject(param="env.debug")],

    # This is a regular FastAPI dependency.
    lucky_number: Annotated[int, Depends(get_lucky_number)]
): ...

@app.websocket("/ws")
async def ws(websocket: WebSocket, greeter: Annotated[GreeterService, Inject()]):
    ...

# Initialize the integration.
# Must be called after all routers have been added.
# service_modules is a list of top-level modules with service registrations.
container = wireup.create_container(
    service_modules=[services], 
    parameters=get_settings_dict()
)
wireup.integration.fastapi.setup(container, app)
```

## Use Wireup in FastAPI Depends

To help with migration, it is possible to use Wireup in FastAPI depends
or anywhere you have a reference to the FastAPI application instance.


```python
async def some_route_or_fastapi_dependency(
    greeter: Annotated[GreeterService, WireupService(GreeterService)],
    foo_param: Annotated[str, WireupParameter("foo")],
    foo_foo: Annotated[str, WireupExpr("${foo}-${foo}")],
    container: Annotated[DependencyContainer, WireupContainer()],
): ...
```


If you're not storing the container in a variable somewhere, you can get a reference
to it by using the `wireup.integration.fastapi.get_container` function.

```python title="example_middleware.py"
from wireup.integration.fastapi import get_container

async def example_middleware(request: Request, call_next) -> Response:
    container = get_container(request.app)
    ...

    return await call_next(request)
```


In the same way, you can get a reference to it in a fastapi dependency.
```python
from wireup.integration.fastapi import get_container

async def example_dependency(request: Request, other_dependency: Annotated[X, Depends(...)]):
    container = get_container(request.app)
    ...
```

### FastAPI request

A key feature of the integration is to expose `fastapi.Request` and `starlette.requests.Request` objects in wireup.

Services depending on it should be transient, so that you get a fresh copy 
every time with the current request being processed.

```python
@service(lifetime=ServiceLifetime.TRANSIENT)
class HttpAuthenticationService:
    def __init__(self, request: fastapi.Request) -> None: ...


@service(lifetime=ServiceLifetime.TRANSIENT)
def example_factory(request: fastapi.Request) -> ExampleService: ...
```

### Testing

For general testing tips with Wireup refer to the [test docs](../testing.md). 
With the FastAPI integration you can override dependencies in the container as follows.

```python title="test_thing.py"
from wireup.integration.fastapi import get_container

def test_override():
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_container(app).override.service(GreeterService, new=DummyGreeter()):
        res = self.client.get("/greet?name=Test")
```

See [FastAPI integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/test_fastapi_integration.py)
for more examples.

## Api Reference

* [fastapi_integration](../class/fastapi_integration.md)
