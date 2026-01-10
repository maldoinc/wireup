# Direct Container Access in FastAPI

Wireup primarily handles dependency injection in FastAPI routes. However, you can directly access the request or application container to retrieve services when needed outside of standard dependency injection.


```python
from wireup.integration.fastapi import get_app_container, get_request_container

# Access the request-scoped container (used for the current request).
# This is what you almost always want.
# It has all the information the app container has in addition
# to data specific to the current request.
request_container = get_request_container()

# Access the application-wide container (created via `wireup.create_async_container`).
# Use this when you need the container outside of the request context lifecycle.
app_container = get_app_container(app)
```

### Container Availability

The app container is always retrievable given an instance of the application.

If you need the request-scoped container outside the route handler (middleware, FastAPI dependencies, decorators), enable `middleware_mode` during setup. 

Normally, the container is created just before the route handler is called, and only on endpoints with Wireup dependencies. With this mode enabled, the request-scoped container is created at the start of the request lifecycle, making it available everywhere. This offers the greatest flexibility but runs on every request.

```python
@router.get("/users")
@require_authn  # Request container is available here
async def get_users(user_service: Injected[UserService]):  # And here
    pass
```

### Examples Using Middleware Mode

#### In Route Decorators

```python hl_lines="4"
def require_not_bob(fn):
    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = await get_request_container().get(fastapi.Request)

        if request.query_params.get("name") == "Bob":
            raise HTTPException(status_code=401, detail="Bob is not allowed")

        return await fn(*args, **kwargs)

    return wrapper

@router.get("/users")
@require_not_bob
async def get_users(user_service: Injected[UserService]):
    ...
```

#### In Middleware (Requires Middleware Mode)

```python hl_lines="4"
from wireup.integration.fastapi import get_request_container

async def example_middleware(request: Request, call_next) -> Response:
    container = get_request_container()
    ...
    return await call_next(request)
```

#### In FastAPI Dependencies (Requires Middleware Mode)

```python hl_lines="6"
from wireup.integration.fastapi import get_request_container

async def get_example_dependency(
    request: Request, 
    other_dependency: Annotated[Other, Depends(...)]
):
    container = get_request_container()
    ...

@router.get("/users")
async def get_users(example: Annotated[Example, Depends(get_example_dependency)]):
    ...
```

    !!! warning
        Mixing Wireup and `fastapi.Depends` is discouraged and should be avoided unless necessary.

        Keep in mind that while accessing the Wireup container in FastAPI dependencies is possible, the reverse is not: Wireup services cannot depend on objects provided by `fastapi.Depends`.
        ...
