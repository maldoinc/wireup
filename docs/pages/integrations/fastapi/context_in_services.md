---
description: Inject fastapi.Request and fastapi.WebSocket into Wireup scoped services for request, security, and connection-aware service logic.
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


## FastAPI Security and OAuth Scopes

Keep OAuth, `Security(...)`, and OpenAPI scope declarations in FastAPI's security system. After the security dependency
resolves the authenticated user, store the value on `request.state`; scoped Wireup services can then read it through the
injected `fastapi.Request`.

```python
from typing import Annotated, NewType

from fastapi import Request, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from wireup import Injected, injectable

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={"profile": "Read the current user's profile"},
)

CurrentUserId = NewType("CurrentUserId", str)


async def load_current_user(
    request: Request,
    security_scopes: SecurityScopes,
    token: Annotated[str, Security(oauth2_scheme)],
) -> None:
    user_id = await verify_token(token, security_scopes.scopes)
    request.state.current_user_id = user_id


@injectable(lifetime="scoped")
def current_user_id_factory(request: Request) -> CurrentUserId:
    return CurrentUserId(request.state.current_user_id)


@app.get("/me", dependencies=[Security(load_current_user, scopes=["profile"])])
async def me(user_id: Injected[CurrentUserId]):
    return {"user_id": user_id}
```

This keeps FastAPI responsible for security dependencies and generated OpenAPI documentation, while Wireup remains
responsible for service wiring after the request context has been established.
