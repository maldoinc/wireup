# Class-Based Handlers for FastAPI

Wireup provides class-based handlers for FastAPI that enables dependency injection with zero runtime overhead.

### Benefits

- Zero runtime overhead for constructor-injected dependencies
- State persistence between requests within the same class
- Better code organization through class-based endpoint grouping

### Basic Usage

Create a class with a field `router` of type `fastapi.Router` then decorate class methods like you normally do.
Register class-based handlers during setup through Wireup. Do not include these routers in fastapi directly. 

```python title="Class-Based Handler example"
class UserHandler:
    router = fastapi.Router(prefix="/users", route_class=WireupRoute)  # (1)!

    def __init__(self, user_service: UserProfileService) -> None:  # (2)!
        self.user_service = user_profile_service


    @router.get("/")
    async def list_all(self):
        return self.user_service.find_all()

    @router.get("/me")
    async def get_current_user_profile(
        self,
        auth_service: Injected[AuthenticationService]  # (3)!
    ) -> web.Response:
        return self.user_service.get_profile(auth_service.current_user)
```

1. Define a router for this class. Tip: Use `route_class=WireupRoute` if you have dependencies being injected in route handlers (methods decorated with `@router`).
2. Inject dependencies directly in the constructor. This is a one-time operation and has no runtime overhead.
3. Request dependencies as usual in FastAPI routes. `AuthenticationService` is a request-scoped dependency, injected using `Injected[T]`.


The router instance is a regular FastAPI router so you can handle any connections in your class-based handlers,
including WebSockets.


### Integration

```python
wireup.integration.fastapi.setup(
    container,
    app,
    class_based_handlers=[UserProfileHandler]
)
```

### How Dependencies Work

1. **Constructor Dependencies**
     - Injected once at startup
     - No `Injected[T]` syntax needed
     - Cannot be overridden after startup
     - Only parameters and singleton services

1. **Route Dependencies**
      - Use `Injected[T]` syntax
      - Supports all scopes
      - Injected per-request

!!! note "Testing"
    FastAPI lifespan events are used for initialization. When testing, create clients as context managers:
    ```python
    @pytest.fixture()
    def client(app: FastAPI) -> Iterator[TestClient]:
        with TestClient(app) as client:
            yield client
    ```
