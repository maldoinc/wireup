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
