# Direct Container Access in FastAPI

Wireup primarily handles dependency injection in FastAPI routes. However, you can directly access the request or application container to retrieve services or configurations when needed.

```python
from wireup.integration.fastapi import get_app_container, get_request_container

# Access the request-scoped container (used for the current request).
request_container: ScopedAsyncContainer = get_request_container()

# Access the application-wide container (created via `wireup.create_async_container`).
app_container: AsyncContainer = get_app_container(app)
```

### Request-Scoped Container Availability

The exact point when the request-scoped container is created,
depends on the `expose_container_in_middleware` setting in the `setup` call.

#### Default (`expose_container_in_middleware=False`)

The container is created just before the route handler is called and is only accessible within the handler or its decorators.

```python
@router.get("/users")
@require_authn  # Container is available here
async def get_users(user_service: Injected[UserService]):  # And here
    pass
```

#### Middleware Mode (`expose_container_in_middleware=True`)

The container is created at the start of the request lifecycle, making it accessible throughout,
including in middleware and fastapi's own dependencies.

### Usage Examples

#### In Route Decorators

```python
def require_not_bob(fn):
    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = await get_request_container().get(Request)
        if request.query_params.get("name") == "Bob":
            raise HTTPException(status_code=401, detail="Bob is not allowed")
        return await fn(*args, **kwargs)
    return wrapper

@router.get("/users")
@require_not_bob
async def get_users(user_service: Injected[UserService]):
    ...
```

#### In Middleware

> Requires Middleware Mode.

```python
from wireup.integration.fastapi import get_request_container

async def example_middleware(request: Request, call_next) -> Response:
    container = get_request_container()
    ...
    return await call_next(request)
```

#### In FastAPI Dependencies

> Requires Middleware Mode.

```python
from wireup.integration.fastapi import get_request_container

async def example_dependency(request: Request, other_dependency: Depends(...)):
    container = get_request_container()
    ...
```

!!! warning
    Use the Wireup container in `fastapi.Depends` sparingly.
    You should avoid using both dependency injection systems in your application.
    
    Note that while this works, the opposite does not. Wireup services cannot depend on `fastapi.Depends` objects.


