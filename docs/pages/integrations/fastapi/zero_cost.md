Wireup enables zero-cost runtime dependency injection in FastAPI through class-based routes for singleton services.
This approach eliminates the overhead of creating dependencies for each request, making your application more efficient.

### Key Benefits
- Zero runtime overhead for dependency injection.
- Dependencies initialized only once at startup.
- Class-based routes for better organization.


!!! note
    Note that zero-cost injection is only available for singleton services (or if coming from fastapi.Depends,
    services which always result in the same instance and are possible decorated with `@lru_cache`/`@cache`.)

    Services which need per-request scope will need to be initialized on every request.

### Existing approach

Existing approaches invoke the dependency injection mechanism even though it will always result in the same instance,
resulting in increased processing overhead.

```python
router = fastapi.APIRouter(prefix="/users")


# Using Wireup in regular routes.
@router.get("/")
async def get_users(user_service: Injected[UserService]):
    return self.user_service.find_all()

# Regular fastapi.Depends injection.
@router.get("/")
async def get_users(
    user_service: Annotated[UserService, fastapi.Depends(get_user_service)]
):
    return self.user_service.find_all()
```

### Zero-Cost example

```python title="app/routes/greeter.py"
class UsersController:
    router = fastapi.APIRouter(prefix="/users")

    def __init__(self, user_service: UserService) -> None:
        self.user_service = user_service

    @router.get("/")
    async def get_users(self):
        return self.user_service.find_all()
```
```python title="app/app.py"

wireup.integration.fastapi.setup(
    container, 
    app, 
    # Let Wireup know of all your class-based routes.
    class_based_routes=[UsersController],
    # Wireup adds its own middleware to enable the following features:
    # - Provide Wireup with access to the current request
    # - Allows you to retrieve Wireup container in middleware.
    # If neither of those features is required, you can disable the middleware.
    enable_middleware=False
)
```

### Middleware

Wireup adds its own middleware to enable the following features:
- Provide Wireup with access to the current request
- Allows you to retrieve Wireup container in middleware.

If neither of those features is required, you can disable the middleware
by passing `enable_middleware=False` to the `wireup.integration.fastapi` call.

!!! tip
    You can re-enable middleware later if you need transient/scoped dependencies or request access.