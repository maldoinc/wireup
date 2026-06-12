---
description: Inject dependencies into FastAPI HTTP and WebSocket route handlers with Wireup using Injected and config annotations.
---

# Inject in Routes

Use `Injected[T]` in FastAPI HTTP and WebSocket handlers.

## HTTP Route Injection

```python
from typing import Annotated
from fastapi import Header
from wireup import Inject, Injected


@app.get("/users")
async def users(
    # Inject services
    service: Injected[UserService],
    # Inject config values
    is_debug: Annotated[bool, Inject(config="debug")],
    # Regular FastAPI dependencies still work
    user_agent: Annotated[str | None, Header()] = None,
): ...
```

## WebSocket Route Injection

```python
from fastapi import WebSocket
from wireup import Injected


@app.websocket("/ws")
async def ws(
    websocket: WebSocket,
    greeter: Injected[GreeterService],
): ...
```

For injecting `fastapi.Request` and `fastapi.WebSocket` into scoped services, see
[Request and WebSocket Context in Services](context_in_services.md).

## Improve Injection Performance

Use `WireupRoute` as the `route_class` for your FastAPI routers to improve injection performance.

```python
from wireup.integration.fastapi import WireupRoute

router = fastapi.APIRouter(route_class=WireupRoute)
```

By default, FastAPI inspects every route parameter and will try to resolve even those meant only for Wireup.
`WireupRoute` hides Wireup-specific parameter names (`Injected[...]`, `Annotated[..., Inject(...)]`)
from FastAPI, avoiding duplicated processing.

It is an optional optimization and not required for injection to work, but recommended for better performance.
Set it on every router individually that uses Wireup injection.
