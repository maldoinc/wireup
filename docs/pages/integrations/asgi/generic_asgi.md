# ASGI Integration

Dependency injection for generic ASGI applications is available in the `wireup.integration.asgi` module.

This integration is framework-agnostic and works with any ASGI framework.

### Initialize the integration

First, [create an async container](../../container.md):

```python
import wireup

container = wireup.create_async_container(injectables=[services])
```

If your framework has native middleware registration, use that first:

```python
from wireup.integration.asgi import WireupASGIMiddleware

app.add_middleware(WireupASGIMiddleware, container=container)
```

If it does not provide middleware registration, wrap it directly:

```python
from wireup.integration.asgi import WireupASGIMiddleware

asgi_app = WireupASGIMiddleware(asgi_app, container)
```

### Inject in Request Path Code

Use `@inject` anywhere in the HTTP/WebSocket request path:

```python
from wireup import Injected
from wireup.integration.asgi import inject


@inject
async def handler(service: Injected[MyService]) -> None:
    ...
```

### Accessing the Request Container

```python
from wireup.integration.asgi import get_request_container

request_container = get_request_container()
```

`get_request_container()` is only available during an active HTTP/WebSocket request.

### App-Level Container Access

This generic integration does not attach the container to your app object automatically.
If your framework/application exposes an app-level state object, store the container there in your app bootstrap code.
This is useful for test overrides and startup/shutdown orchestration.

```python
# fictional app state object
app.state.container = container
```

Example test override pattern:

```python
from wireup.integration.asgi import WireupASGIMiddleware


def create_app():
    container = wireup.create_async_container(injectables=[services])
    app = build_asgi_app()
    app.state.container = container
    app = WireupASGIMiddleware(app, container)
    return app


def test_override():
    app = create_app()
    with app.state.container.override.injectable(MyService, new=MyFakeService()):
        ...
```

### Container Shutdown

The generic ASGI integration does not manage application shutdown lifecycle.

If you use resource factories (for example, factories that `yield`), you must close the container from your host
framework's lifespan/shutdown hook:

```python
await container.close()
```

### API Reference

Visit [API Reference](../../class/asgi_integration.md) for details.
