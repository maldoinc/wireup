# Class-Based Routes for FastAPI

Wireup introduces **class-based routes** for FastAPI, offering a **zero-cost dependency injection** mechanism that ensures efficient and scalable applications.

### Key Features

- **Zero-Cost Injection**: No runtime overhead for dependencies defined in the init method.
- **Stateful Handlers**: Persist state across requests for enhanced functionality.
- **Logical Grouping**: Organize related endpoints within a single class.

### Example Usage

```python
class UserProfileHandler:
    router = fastapi.Router(prefix="/users", route_class=WireupRoute)  # (1)!

    def __init__(self, user_service: UserProfileService) -> None:  # (2)!
        self.user_service = user_profile_service

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


The router instance is a regular FastAPI router so you can handle any connections in your class-based routes,
including WebSockets.


### Integration

```python
wireup.integration.fastapi.setup(
    container,
    app,
    # Register class-based handlers during setup.
    # Do NOT include these routers in fastapi directly. 
    class_based_routes=[UserProfileHandler]
)
```

### Dependency Management

- **Constructor Injection**: Dependencies injected into the constructor do not require the `Injected` syntax.
- **Route-Specific Injection**: Use `Injected[T]` for transient or scoped dependencies within route methods.
- **Overriding**: Dependencies injected into the constructor cannot be overridden after application startup. Ensure overrides happen before the application starts.


!!! warning
    This feature makes use of FastAPI's lifespan events. For this to properly function in your tests you must create
    the test client as a context manager.

    ```python
    @pytest.fixture()
    def client(app: FastAPI) -> Iterator[TestClient]:
        with TestClient(app) as client:
            yield client
    ```