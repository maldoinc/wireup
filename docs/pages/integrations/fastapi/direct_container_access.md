# Direct Container Access in FastAPI

Wireup primarily handles dependency injection in FastAPI routes. However, you can directly access the request or application container to retrieve services or configurations when needed.

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

The app container can always be retrieved. The exact point when the request-scoped container is created,
depends on the `middleware_mode` setting in the `setup` call.

#### Default (`middleware_mode=False`)

The container is created just before the route handler is called and is only accessible within the handler or its decorators.

```python
@router.get("/users")
@require_authn  # Request container is available here
async def get_users(user_service: Injected[UserService]):  # And here
    pass
```

#### Middleware Mode (`middleware_mode=True`)

The container is created at the start of the request lifecycle, making it accessible throughout,
including in middleware and fastapi's own dependencies. While this mode offers greater flexibility,
it is off by default as the middleware will run on every request to create a scoped container, as opposed to only when strictly necessary.

### Usage Examples

#### In Route Decorators

```python
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

```python
from wireup.integration.fastapi import get_request_container

async def example_middleware(request: Request, call_next) -> Response:
    container = get_request_container()
    ...
    return await call_next(request)
```

#### In FastAPI Dependencies (Requires Middleware Mode)

```python
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
    Mixing Wireup and `fastapi.Depends` in an application is strongly discouraged
    and should be avoided unless absolutely necessary.

    If some third-party library modifies the request state with useful information
    you can access the fastapi request directly from Wireup and make the data available
    to other Wireup services.
    
    Keep in mind that although accessing the Wireup container in FastAPI dependencies is possible, the reverse is not: Wireup services cannot depend on objects provided by `fastapi.Depends`.


