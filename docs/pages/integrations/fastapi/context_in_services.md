---
description: Inject fastapi.Request and fastapi.WebSocket into Wireup scoped services for request and connection-aware service logic.
---

# Request and WebSocket Context in Services

Inject `fastapi.Request` or `fastapi.WebSocket` into scoped services when your service logic needs connection context.

## Enable Request/WebSocket Context Injection

Include the FastAPI integration module in container injectables:

```python
import wireup
import wireup.integration.fastapi

container = wireup.create_async_container(
    injectables=[services, wireup.integration.fastapi],
)
```

## Inject `fastapi.Request`

```python
import fastapi
from wireup import injectable


@injectable(lifetime="scoped")
class HttpAuthenticationService:
    def __init__(self, request: fastapi.Request) -> None:
        self.request = request

    def current_user_id(self) -> str:
        return self.request.headers["x-user-id"]
```

## Inject `fastapi.WebSocket`

```python
import fastapi
from wireup import injectable


@injectable(lifetime="scoped")
class WebSocketSessionService:
    def __init__(self, websocket: fastapi.WebSocket) -> None:
        self.websocket = websocket

    async def send_welcome(self) -> None:
        await self.websocket.send_text("connected")
```

## Use Alongside Route Injection

Route handlers still use `Injected[...]` as usual:

```python
from wireup import Injected


@app.get("/me")
async def me(auth: Injected[HttpAuthenticationService]):
    return {"user_id": auth.current_user_id()}
```

For route signature patterns, see [Inject in Routes](inject_in_routes.md).
