# Class-Based Handlers for FastAPI

Wireup provides class-based handlers for FastAPI allowing grouping of related endpoints and dependency injection with
zero runtime overhead.

### Benefits

- Zero runtime overhead for constructor-injected dependencies
- State persistence between requests within the same class
- Better code organization through class-based endpoint grouping

### Basic Usage

Create a class with a field `router` of type `fastapi.Router` then decorate class methods like you normally do. Register
class-based handlers during setup through Wireup. Do not include these routers in fastapi directly.

```python title="Class-Based Handler example"
class UserHandler:
    router = fastapi.APIRouter(prefix="/users", route_class=WireupRoute)  # (1)!

    def __init__(self, user_service: UserProfileService) -> None:  # (2)!
        self.user_service = user_service

    @router.get("/")
    async def list_all(self):
        return self.user_service.find_all()

    @router.get("/me")
    async def get_current_user_profile(
        self,
        auth_service: Injected[AuthenticationService],  # (3)!
    ) -> fastapi.Response:
        return self.user_service.get_profile(auth_service.current_user)
```

1. Define a router for this class. Tip: Use `route_class=WireupRoute` if you have dependencies being injected in route
    handlers (methods decorated with `@router`).
1. Inject dependencies directly in the constructor. This is a one-time operation and has no runtime overhead.
1. This is treated just like any other FastAPI route and as such, use of `Injected[T]` is required.
    `AuthenticationService` is a request-scoped dependency.

The router instance is a regular FastAPI router so you can handle any connections in your class-based handlers,
including WebSockets.

### Integration

```python
wireup.integration.fastapi.setup(
    container, app, class_based_handlers=[UserProfileHandler]
)
```

### How Dependencies Work

1. **Constructor Dependencies**

    - Injected once at startup
    - No `Injected[T]` syntax needed
    - Cannot be overridden after startup
    - Only configuration and singleton services

1. **Route Dependencies**

    - Use `Injected[T]` syntax
    - Supports all scopes\*
    - Injected per-request

\* Injecting configuration and singletons here has no benefit and is not zero-cost. Inject those in `__init__` instead.

!!! note "Testing"

    This feature uses FastAPI lifespan events. When testing, create the test client using a context manager for the lifespan
    events to correctly trigger. Note that this is a limitation of Fastapi/Testclient rather than Wireup.

    ```python
    @pytest.fixture()
    def client(app: FastAPI) -> Iterator[TestClient]:
        with TestClient(app) as client:
            yield client
    ```
