Dependency injection for AIOHTTP is available in the `wireup.integration.aiohttp` module.

**Features:**

- [x] Inject dependencies in AIOHTTP handlers.
- [x] Expose `aiohttp.web.Request` as a `scoped` Wireup dependency.
- [x] Close the Wireup container on application termination for proper resource cleanup.
- [x] Real class-based handlers in AIOHTTP.

---

### Initialize the integration

To initialize the integration, call `wireup.integration.aiohttp.setup` after adding all routes.

```python
container = wireup.create_async_container(
    # Add service modules.
    service_modules=[
        # Top level module containing service registrations.
        services,
        # Add this module if you need `aiohttp.web.Request` in Wireup services.
        wireup.integration.aiohttp
    ],
    # Expose parameters to Wireup as necessary. 
    parameters={"db_dsn": os.environ.get("APP_DB_DSN")}
)
wireup.integration.aiohttp.setup(container, app)
```

### Inject in AIOHTTP handlers

To inject dependencies, add the type to the handler's signature and annotate them as necessary.
See [Annotations](../annotations.md) for more details.

=== "Function Handlers"

    ```python title="HTTP Handler"
    async def get_users(
        request: aiohttp.web.Request,
        user_repository: Injected[UserRepository],
    ) -> aiohttp.web.Response:
        ...
    ```

=== "Class-Based Views"
    Class-based views work the same, but the dependencies must be declared in the init method. 

    ```python title="Class Based View"
    class UsersView(aiohttp.web.View):
        def __init__(
            self, 
            request: web.Request, 
            user_repository: Injected[UserRepository],
        ) -> None:
            super().__init__(request)
            self.user_repository = user_repository

        async def get() -> aiohttp.web.Response: ...
    ```

### Class-based handlers

Wireup allows you to define class-based handlers, similar to the example in the [AIOHTTP Documentation](https://docs.aiohttp.org/en/stable/web_quickstart.html#organizing-handlers-in-classes).

Unlike per-request views, class-based handlers are instantiated once, enabling them to maintain state and avoid redundant dependency injections.

For example, if `GreeterService` is a singleton, injecting it repeatedly in per-request views results in unnecessary work to return the same instance. Class-based handlers eliminate this overhead by performing the injection only once.

Wireup instantiates the handler and injects its dependencies once, avoiding repeated work for each request.

```python title="Class-Based Handler powered by Wireup"
class GreeterHandler:
    router = web.RouteTableDef() #(1)!

    def __init__(self, greeter: GreeterService) -> None: #(2)!
        self.greeter = greeter
        self.counter = 0

    @router.get("/greet")
    async def get_thing(
        self,
        request: web.Request, #(3)!
        auth_service: Injected[AuthenticationService] #(4)!
    ) -> web.Response:
        self.counter += 1

        return web.json_response(
            {
                "greeting": self.greeter.greet(request.query.get("name", "world")),
                "counter": self.counter,
            }
        )
```

1. The class MUST contain a `aiohttp.web.RouteTableDef` instance named `router`.
2. When injecting in the constructor the `Injected` syntax is not required.
3. As usual with AIOHTTP handlers, the first argument must be `web.Request`.
4. Other dependencies can be requested in the routes. These can be of any scope.


!!! tip "Godo to know" 
    **Handler rules**:

    * Handlers can only depend on Wireup singleton services or parameters.
    * AIOHTTP routes must be defined in a `router` class instance member of type `web.RouteTableDef`.
    * Use the `router` to decorate class methods as route handlers.

    **Registration**: Do not register these routers with your application, instead pass them to the Wireup Integration.

    ```python
    wireup.integration.aiohttp.setup(
        container,
        app,
        handlers=[GreeterHandler]
    )
    ```

    **Overriding**: Since handlers are created once on startup, their dependencies cannot be overridden once the application
    starts. If you need to override dependencies in the handler's init it must be done before application
    startup.

### Inject AIOHTTP request

A key feature of the integration is to expose `aiohttp.web.Request` in Wireup.
To allow injecting it in your services you must add `wireup.integration.aiohttp` module to your service modules
when creating a container.

```python
@service(lifetime="scoped")
class HttpAuthenticationService:
    def __init__(self, request: aiohttp.web.Request) -> None: ...


@service(lifetime="scoped")
def example_factory(request: aiohttp.web.Request) -> ExampleService: ...
```

### Accessing the Container

If you ever need to access the Wireup container directly, use the provided functions:

```python
from wireup.integration.aiohttp import get_app_container, get_request_container

# Get application-wide container.
app_container: AsyncContainer = get_app_container(app)

# Get request-scoped container.
# This is what is currently injecting services on the active request.
request_container: ScopedAsyncContainer = get_request_container()
```

### Get dependencies in middleware

Wireup integration performs injection only in AIOHTTP handlers. If the container is not stored globally, you can get a reference to it using `get_app_container` and `get_request_container` from the `wireup.integration.aiohttp` module.

```python title="example_middleware.py"
from wireup.integration.aiohttp import get_request_container

@web.middleware
async def example_middleware(request: aiohttp.web.Request, handler):
    container = get_request_container()
    ...

    return await handler(request)
```

### Testing

For general testing tips with Wireup refer to the [test docs](../testing.md). 
With the AIOHTTP integration, you can override dependencies in the container as follows.

```python title="test_thing.py"
from wireup.integration.aiohttp import get_app_container

def test_override(aiohttp_client):
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_app_container(app).override.service(GreeterService, new=DummyGreeter()):
        res = aiohttp_client.get("/greet?name=Test")
```

See [AIOHTTP integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/test_aiohttp_integration.py)
for more examples.

## API Reference

* [aiohttp_integration](../class/aiohttp_integration.md)
