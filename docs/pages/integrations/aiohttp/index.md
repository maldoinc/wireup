# AIOHTTP Integration

Dependency injection for AIOHTTP is available in the `wireup.integration.aiohttp` module.

**Features:**

- [x] Inject dependencies in AIOHTTP handlers.
- [x] Expose `web.Request` as a `scoped` Wireup dependency.
- [x] Close the Wireup container on application termination for proper resource cleanup.
- [x] Class-based handlers in AIOHTTP.

---

### Initialize the integration

To initialize the integration, call `wireup.integration.aiohttp.setup`.

```python
container = wireup.create_async_container(
    # Add service modules.
    service_modules=[
        # Top level module containing service registrations.
        services,
        # Add this module if you need `web.Request` in Wireup services.
        wireup.integration.aiohttp
    ],
    # Expose parameters to Wireup as necessary. 
    parameters={"db_dsn": os.environ.get("APP_DB_DSN")}
)
wireup.integration.aiohttp.setup(container, app)
```

### Inject in AIOHTTP handlers

To inject dependencies, add the type to the handler's signature and annotate them as necessary.
See [Annotations](../../annotations.md) for more details.

=== "Function Handlers"

    ```python title="Function Handler"
    async def get_users(
        request: web.Request,
        user_repository: Injected[UserRepository],
    ) -> web.Response:
        ...
    ```

=== "Class-Based Views"
    In Class-based views dependencies must be declared in the init method. 

    ```python title="Class Based View"
    class UsersView(web.View):
        def __init__(
            self, 
            request: web.Request, 
            user_repository: Injected[UserRepository],
        ) -> None:
            super().__init__(request)
            self.user_repository = user_repository

        async def get() -> web.Response: ...
    ```


### Inject AIOHTTP request

A key feature of the integration is to expose `web.Request` in Wireup.
To allow injecting it in your services you must add `wireup.integration.aiohttp` module to your service modules
when creating a container.

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


### Routes and type checker

If you're using a type checker, then you may notice it showing type errors when adding
dependencies to aio handlers. This is because the signature as defined in aiohttp only allows for `web.Request` in the parameters. To make the type checker happy you can annotate them with `wireup.integration.aiohttp.route`.

```python hl_lines="4"
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
