# Class-Based Handlers for AIOHTTP

Class-based handlers in Wireup provide a new mechanism for efficient dependency injection for AIOHTTP applications. They
optimize performance by managing dependencies at startup rather than per request. Dependencies injected in the init
method are zero-cost.

### Key Benefits

- **Request Performance**: Zero overhead from dependency resolution during request handling.
- **Stateful Handlers**: Maintain state across requests.
- **Route set**: Group relevant resource endpoints together

### Example

```python title="greeter.py"
class GreeterHandler:
    router = web.RouteTableDef()  # (1)!

    def __init__(self, greeter: GreeterService) -> None:  # (2)!
        self.greeter = greeter
        self.counter = 0

    @router.get("/greet")
    async def get_thing(
        self,
        request: web.Request,  # (3)!
        auth_service: Injected[AuthenticationService],  # (4)!
    ) -> web.Response:
        self.counter += 1

        return web.json_response(
            {
                "greeting": self.greeter.greet(
                    request.query.get("name", "world")
                ),
                "counter": self.counter,
            }
        )
```

1. The class must contain a `web.RouteTableDef` instance named `router`. Use it to decorate routes inside this class.
1. When injecting in the constructor the `Injected` syntax is not required.
1. Like every AIOHTTP request handler, the first argument must be `web.Request`.
1. Other scoped/transient dependencies can be requested in the routes. Here the `Injected[T]` annotation is required.

```python title="app.py"
wireup.integration.aiohttp.setup(container, app, handlers=[GreeterHandler])
```

**Overriding**: Handlers are created once on startup, their dependencies cannot be overridden once the application
starts. If you need to override dependencies in the handler's `__init__`, then it must be done before application
startup.
