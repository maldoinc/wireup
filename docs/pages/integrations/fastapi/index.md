---
description: >-
  FastAPI dependency injection with Wireup: type-safe DI for routes, WebSockets, request-time injection, class-based handlers, and background tasks.
---

# :simple-fastapi:{.color-fastapi} FastAPI Integration

<div class="grid cards annotate" markdown>

- :material-transit-connection-variant:{ .lg .middle } __Deep Integration__

    ______________________________________________________________________

    Inject anywhere in the request path, not just route handlers, without manually threading dependencies through each call.

    [:octicons-arrow-right-24: Learn more](request_time_injection.md)

- :material-speedometer:{ .lg .middle } __Zero Runtime Overhead__

    ______________________________________________________________________

    Inject dependencies with **zero** runtime overhead using Class-Based Handlers.

    [:octicons-arrow-right-24: Learn more](class_based_handlers.md)

- :material-timer-cog-outline:{ .lg .middle } __Background Tasks__

    ______________________________________________________________________

    Inject dependencies into scheduled background callbacks via `WireupTask`.

    [:octicons-arrow-right-24: Learn more](background_tasks.md)

- :material-share-circle:{ .lg .middle } __Framework-Agnostic__

    ______________________________________________________________________

    Share your service layer with CLI tools, background workers, and other frameworks.

</div>

!!! tip "Migrating from FastAPI Depends?"

    Evaluating Wireup for your FastAPI project? Check out the migration page which includes common pain points with FastAPI Depends and how to solve them with Wireup as well
    as a low-friction migration path:

    [Migrate from FastAPI Depends to Wireup](../../migrate_to_wireup/fastapi_depends.md).

## Quick Start

This is the shortest path to a working FastAPI endpoint with Wireup injection.

```python title="main.py"
from fastapi import FastAPI
import wireup
import wireup.integration.fastapi
from wireup import Injected, injectable


# 1. Define services
@injectable
class GreeterService:
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"


# 2. Create container
container = wireup.create_async_container(injectables=[GreeterService])

app = FastAPI()


# 3. Use Injected[T] in routes for Wireup injection
@app.get("/")
async def greet(greeter: Injected[GreeterService]):
    return {"message": greeter.greet("World")}


# 4. Initialize Wireup integration
wireup.integration.fastapi.setup(container, app)
```
Best practice is to call `setup(...)` after routes are added.

Run the server with:

```bash
fastapi dev main.py
```

## Dependency Validation

`wireup.integration.fastapi.setup(...)` validates route handlers up front.
For regular route handlers, missing dependencies and config values fail during setup. For Class-based handlers, they fail during app startup.

See [What Wireup Validates](../../what_wireup_validates.md) for the full rules.

## How the Integration Works

The diagrams below show what Wireup does at each stage of a FastAPI application's life.

### App Lifecycle

`setup(...)` wires the container into the app and wraps the FastAPI lifespan, so Wireup runs on startup and shutdown.

```mermaid
sequenceDiagram
    autonumber
    participant App as Your code
    participant Wireup
    participant FastAPI
    participant Container as Wireup container

    Note over App,Container: Container setup
    App->>Container: wireup.create_async_container(injectables=[...])
    App->>FastAPI: app = FastAPI(), add routes

    Note over App,Container: Integration setup
    App->>Wireup: wireup.integration.fastapi.setup(container, app)
    Wireup->>FastAPI: Store container in app.state
    opt middleware_mode=True
        Wireup->>FastAPI: Add WireupAsgiMiddleware
    end
    Wireup->>FastAPI: Wrap the app lifespan
    Wireup->>FastAPI: Wrap routes that use Injected[T]
    Note right of Wireup: Missing dependencies fail here

    Note over App,Container: App startup (lifespan enter)
    FastAPI->>Wireup: Run the wrapped lifespan
    opt class_based_handlers given
        Wireup->>Container: Create each handler class
        Wireup->>FastAPI: Include the handler routers
    end
    Wireup->>FastAPI: Wrap routes added since setup
    Wireup->>App: Enter your original lifespan
    Note over FastAPI: App serves requests

    Note over App,Container: Teardown (lifespan exit)
    FastAPI->>Wireup: Exit the wrapped lifespan
    Wireup->>App: Exit your original lifespan
    Wireup->>Container: container.close()
    Note right of Container: Singleton generator factories run their cleanup
```

### Per-Request Lifecycle

Each request gets its own scope, and where that scope lives depends on `middleware_mode`.
In the default mode, a route that only injects singletons skips scope creation entirely.

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant FastAPI
    participant Middleware as WireupAsgiMiddleware
    participant Wrapper as Wireup route wrapper
    participant Scope as Scoped container
    participant Handler as Route handler

    Client->>FastAPI: HTTP request

    alt Default (middleware_mode=False)
        FastAPI->>Wrapper: Call the route
        Wrapper->>Scope: container.enter_scope({Request: request})
        Wrapper->>Scope: Resolve each Injected[T]
        Scope-->>Wrapper: Singletons are reused, scoped and transient deps are created
        Wrapper->>Handler: Call handler with the injected arguments
        Handler-->>Wrapper: Return value
        Wrapper->>Scope: Exit the scope
        Note right of Scope: Scoped and transient generator factories run their cleanup
        Wrapper-->>FastAPI: Return value
        FastAPI-->>Client: Response
    else middleware_mode=True
        FastAPI->>Middleware: ASGI call
        Middleware->>Scope: container.enter_scope({Request: request})
        Middleware->>Middleware: Store the scope in a context variable
        Middleware->>FastAPI: Continue to the route
        FastAPI->>Wrapper: Call the route
        Wrapper->>Scope: get_request_container(), then resolve each Injected[T]
        Scope-->>Wrapper: Singletons are reused, scoped and transient deps are created
        Wrapper->>Handler: Call handler with the injected arguments
        Handler-->>Wrapper: Return value
        Wrapper-->>FastAPI: Return value
        FastAPI-->>Client: Response
        FastAPI-->>Middleware: Route finished
        Middleware->>Scope: Exit the scope
        Note right of Scope: Scoped and transient generator factories run their cleanup
    end
```

In the default mode the scope closes when the handler returns, before FastAPI sends the response.
With `middleware_mode=True` the scope stays open for the whole request, so request-time helpers such as
[`@inject`](request_time_injection.md) can use it, and it closes after the response is sent.
WebSocket routes always use the default flow, with `WebSocket` in place of `Request`.

## Detailed Guides

- [Inject in Routes](inject_in_routes.md): HTTP/WebSocket handler injection and config value injection in route signatures.
- [Request and WebSocket Context in Services](context_in_services.md): inject `fastapi.Request` and `fastapi.WebSocket` into Wireup services, including FastAPI security/OAuth context.
- [Class-Based Handlers](class_based_handlers.md): zero per-request constructor resolution and `WireupRoute` optimizations.
- [Request-Time Injection](request_time_injection.md): injection in decorators, middleware, and other request-time call sites.
- [Background Tasks](background_tasks.md): inject dependencies into scheduled callbacks with `WireupTask`.
- [FastAPI Testing](testing.md): `TestClient` lifespan usage, overrides, and request-lifecycle tests.
- [Troubleshooting](troubleshooting.md): common setup/runtime errors and fast fixes.

## API Reference

- [fastapi_integration](../../class/fastapi_integration.md)
