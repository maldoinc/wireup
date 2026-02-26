# Request Lifecycle Patterns

While Wireup primarily handles dependency injection in FastAPI routes, you can also use dependencies in other functions during the request lifecycle to create composable and reusable patterns:

- **Reusable Route Decorators**: `@require_admin`, `@require_permission`, `@rate_limit`
- **Middleware Integration**: request context setup and cross-cutting request logic
- **Migration Support**: composing Wireup services with external FastAPI dependencies


!!! info "Advanced Feature - Requires Middleware Mode"

    The patterns shown on this page require `middleware_mode=True` during Wireup setup.

    ```python
    wireup.integration.fastapi.setup(container, app, middleware_mode=True)
    ```

    Normally, the request-scoped container is created just before the route handler is called. With middleware mode enabled, it's created at the start of the request lifecycle, making it available in middleware and other request handlers.


## Composable Route Decorators

Route decorators let you extract cross-cutting concerns into reusable components that can be applied to multiple endpoints. Examples below:

### Authentication & Authorization

```python
from wireup import Injected
from wireup.integration.fastapi import inject


@inject
@contextlib.asynccontextmanager
async def require_permission(
    permission: str,
    auth: Injected[AuthService],
) -> AsyncIterator[None]:
    if not await auth.has_permission(permission):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    yield


@router.get("/users")
@require_permission("read_users")
async def get_users(user_service: Injected[UserService]): ...
```

### Rate Limiting

```python
from wireup import Injected
from wireup.integration.fastapi import inject


@inject
@contextlib.asynccontextmanager
async def rate_limit(
    rate_limiter: Injected[RateLimiterService],
    max_requests: int = 100,
) -> AsyncIterator[None]:
    if not await rate_limiter.check(max_requests):
        raise HTTPException(status_code=429, detail="Too many requests")

    yield


@router.get("/api/data")
@rate_limit(max_requests=50)
async def get_data(data_service: Injected[DataService]): ...
```

## Middleware Integration

Access Wireup services in FastAPI middleware for request setup or other cross-cutting concerns.

### Request-Time Middleware Pattern

FastAPI's dependency system (`Depends`) does not apply to middleware. Middleware runs outside route handlers, so this is
one of the places where FastAPI cannot inject your services for you.

Use `@inject` here when you want request-scoped services in middleware, and run your service layer directly before
passing control to the route handler.

```python
from wireup import Injected
from wireup.integration.fastapi import inject


@app.middleware("http")
@inject
async def request_middleware(
    request: Request,
    call_next,
    request_context: Injected[RequestContextService],
) -> Response:
    await request_context.initialize(request)
    return await call_next(request)
```

## Integrating with FastAPI Dependencies

When migrating to Wireup or composing with external libraries that provide FastAPI dependencies,
you can access Wireup services within `Depends()` functions.

```python
from wireup import Injected
from wireup.integration.fastapi import inject


@inject
async def get_user_dependency(
    request: Request,
    auth_header: Annotated[str, Depends(get_auth_header)],
    auth_service: Injected[AuthService],
    user_service: Injected[UserService],
):
    user = await auth_service.authenticate(auth_header)
    return await user_service.enrich(user)


@router.get("/users")
async def get_users(
    user: Annotated[User, Depends(get_user_dependency)],
    user_service: Injected[UserService],
): ...
```

!!! warning "Avoid When Possible"

    This pattern should be rare. Prefer pure Wireup injection. Use this only when:

    - **Migrating gradually to Wireup** from pure FastAPI `Depends()`
    - **External libraries** require `Depends()` integration

    Remember: Wireup services cannot depend on `Depends()` providers.


## Testing Patterns

When testing code that runs request-time helpers (`@inject` or `get_request_container()`), ensure the request-scoped
container is available.

### Testing Route Decorators

```python
from fastapi.testclient import TestClient
import wireup
import wireup.integration.fastapi


# Set up app with middleware_mode enabled
app = FastAPI()
container = wireup.create_async_container(injectables=[AuthService, UserService])
wireup.integration.fastapi.setup(container, app, middleware_mode=True)


@router.get("/users")
@require_permission("read_users")
async def get_users(user_service: Injected[UserService]): ...


def test_require_permission_denied():
    with TestClient(app) as client:
        # AuthService will be mocked via container overrides
        response = client.get("/users")
        assert response.status_code == 403


def test_require_permission_allowed():
    with TestClient(app) as client:
        # Override AuthService to return True
        with get_app_container(app).override.injectable(
            AuthService, new=MockAuthService(allow=True)
        ):
            response = client.get("/users")
            assert response.status_code == 200
```

### Testing Middleware

```python
def test_request_middleware_runs():
    with TestClient(app) as client:
        response = client.get("/api/users")
        assert response.status_code == 200
```

!!! tip

    Use `get_app_container(app).override.injectable()` to inject mocks and fakes during tests.
    This works for both route decorators and middleware patterns.

## Direct Container Access

For utilities, helpers, or other cases where you need direct access to the container APIs:

```python
from wireup.integration.fastapi import get_app_container, get_request_container

# Access the request-scoped container (used for the current request).
request_container = get_request_container()

# Access the application-wide container (created via `wireup.create_async_container`).
# Use this when you need the container outside of the request context lifecycle.
app_container = get_app_container(app)
```

The app container is always retrievable given an instance of the application. The request-scoped container
is only available when `middleware_mode=True` is enabled.


!!! tip "Prefer `@inject` for request-time helpers"

    `@inject` keeps signatures type-driven and avoids manual container lookups.
    If you prefer explicit container access, `get_request_container()` works anywhere during a request:

    ```python
    from wireup.integration.fastapi import get_request_container


    async def write_audit_log(message: str) -> None:
        audit = await get_request_container().get(AuditService)
        await audit.write(message)
    ```
