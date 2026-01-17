# :simple-aiohttp: AIOHTTP Integration

Dependency injection for AIOHTTP is available in the `wireup.integration.aiohttp` module.

<div class="grid cards annotate" markdown>

-   :material-cog-refresh:{ .lg .middle } __Automatic Dependency Management__

    ---

    Inject dependencies in routes and automatically manage container lifecycle.


-   :material-web-check:{ .lg .middle } __Request Objects__

    ---

    Use request and websocket objects in Wireup dependencies.


-   :material-clock-fast:{ .lg .middle } __Zero Runtime Overhead__

    ---

    Inject dependencies with __zero__ runtime overhead in Class-Based Handlers.

    [:octicons-arrow-right-24: Learn more](class_based_handlers.md)


-   :material-share-circle:{ .lg .middle } __Shared business logic__

    ---

    Wireup is framework-agnostic. Share the service layer between web applications and other interfaces, such as a CLI.
</div>


### Initialize the integration

First, [create an async container](../../container.md).

```python
container = wireup.create_async_container(
    injectables=[services],
    config={"db_dsn": os.environ.get("APP_DB_DSN")}
)
```

Then initialize the integration:

```python
wireup.integration.aiohttp.setup(container, app)
```

### Inject in AIOHTTP handlers

To inject dependencies, add the type to the handler's signature and annotate them as necessary.
See [Annotations](../../annotations.md) for more details.

=== "Function Handlers"

    ```python title="Function Handler" hl_lines="3"
    async def get_users(
        request: web.Request,
        user_repository: Injected[UserRepository],
    ) -> web.Response:
        ...
    ```

=== "Class-Based Views"
    In Class-based views dependencies must be declared in the init method. 

    ```python title="Class Based View" hl_lines="5"
    class UsersView(web.View):
        def __init__(
            self, 
            request: web.Request, 
            user_repository: Injected[UserRepository],
        ) -> None:
            super().__init__(request)
            self.user_repository = user_repository

        async def get(self) -> web.Response: ...
    ```


### Inject AIOHTTP request

To inject `web.Request` in services, include `wireup.integration.aiohttp` module in the injectables
when creating the container.

```python hl_lines="4"
container = wireup.create_async_container(
    injectables=[
        services,
        wireup.integration.aiohttp
    ],
    config={"db_dsn": os.environ.get("APP_DB_DSN")}
)
```

### Accessing the Container

If you need to access the Wireup container directly, use the following functions:

```python
from wireup.integration.aiohttp import get_app_container, get_request_container

# Get application-wide container.
app_container: AsyncContainer = get_app_container(app)

# Get request-scoped container.
# This is what is currently injecting services on the active request.
request_container: ScopedAsyncContainer = get_request_container()
```

### Testing

For general testing tips with Wireup refer to the [test docs](../../testing.md). 
With the AIOHTTP integration, you can override dependencies in the container as follows.

```python title="test_thing.py" hl_lines="8"
from wireup.integration.aiohttp import get_app_container

def test_override(aiohttp_client):
    class DummyGreeter(GreeterService):
        def greet(self, name: str) -> str:
            return f"Hi, {name}"

    with get_app_container(app).override.service(GreeterService, new=DummyGreeter()):
        res = aiohttp_client.get("/greet?name=Test")
```

See [AIOHTTP integration tests](https://github.com/maldoinc/wireup/blob/master/test/integration/aiohttp/test_aiohttp_integration.py)
for more examples.


### Lifecycle Management

The integration automatically manages the container lifecycle. It hooks into AIOHTTP's `on_cleanup` signal to ensure the container is properly closed and resources are released when the application stops.

### Routes and type checker

If you're using a type checker, then you may notice it showing type errors when adding
dependencies to aio handlers. This is because the signature as defined in aiohttp only allows for `web.Request` in the signature. 

To address this, you can decorate the handler with `@wireup.integration.aiohttp.route`.
This decorator is a no-op at runtime but provides the necessary type hints to satisfy type checkers.

```python hl_lines="4 7"
from wireup.integration.aiohttp import route

@router.get("/users")
@route
async def users_list(
    request: web.Request, 
    user_repository: Injected[UserRepository],
) -> web.Response:
    pass
```

### API Reference

* [aiohttp_integration](../../class/aiohttp_integration.md)
