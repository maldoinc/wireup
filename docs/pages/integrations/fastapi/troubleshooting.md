---
description: Troubleshoot Wireup FastAPI integration issues including setup errors, lifespan/test client pitfalls, middleware_mode, and class-based handler caveats.
---

# FastAPI Troubleshooting

Common issues and fixes for Wireup's FastAPI integration.

## Injection is not set up correctly

Symptom:

- You get an error saying injection is not set up correctly when hitting an endpoint.

Fix:

1. Make sure `wireup.integration.fastapi.setup(container, app)` is called.
2. Make sure routes use `Injected[...]` or `@inject` where expected.

```python
container = wireup.create_async_container(
    injectables=[services, wireup.integration.fastapi]
)
app = FastAPI()

wireup.integration.fastapi.setup(container, app)
```

## Tests fail but app works

Symptom:

- Injection or startup behavior fails in tests.

Fix:

Use `TestClient` as a context manager so FastAPI lifespan runs.

```python
def test_endpoint(app: FastAPI):
    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200
```

## `get_request_container()` is unavailable in middleware/helpers

Symptom:

- `get_request_container()` raises `WireupError` in middleware or request-time decorators/helpers.

Fix:

1. Call setup with `middleware_mode=True`.
2. Make sure Wireup middleware is outermost (middleware ordering matters).

```python
wireup.integration.fastapi.setup(container, app, middleware_mode=True)
```

## `get_request_container()` is unavailable in WebSocket handlers

Symptom:

- `get_request_container()` raises inside WebSocket routes.

Why:

- Middleware-backed request containers in FastAPI are HTTP-only.

Fix:

- Prefer `Injected[...]` in websocket handlers/services.
- Use `get_app_container(app)` outside request scope if needed.

## Middleware added after `setup(...)`

Symptom:

- Request-container behavior in middleware is inconsistent.

Fix:

- Add middleware before calling `setup(...)`.
- If middleware needs request-scoped DI, also enable `middleware_mode=True`.

## Class-based handlers fail with “endpoint has been modified”

Symptom:

- Error says class-based handler method was modified (often by route decorators).

Fix:

- For class-based handlers, make sure endpoint methods are not wrapped after router registration.
- If decorating methods, place decorators before router registration and follow the class-based handlers guide.

See [Class-Based Handlers](class_based_handlers.md) for the supported pattern.
