# Class-Based Routes

Wireup provides true zero-cost dependency injection for FastAPI through Class-Based Routes.

This pattern allows you to define reusable controllers that are instantiated once at startup,
improving code organization and performance by avoiding unnecessary runtime injection.

### Implementation

1. Request dependencies in the `__init__` method.
1. Define a `router` field of type `fastapi.APIRouter` inside the class.
1. Use the router to decorate routes like you normally do in FastAPI.
2. If the routes need scoped/transient dependencies, you can ask for them in the route as usual. 
3. Register the class when calling `wireup.integration.fastapi.setup` instead of including it in via FastAPI.

Here's a complete example:

```python title="app/routes/users.py"
class UsersController:
    router = fastapi.APIRouter(prefix="/users")

    # Constructor dependencies are injected once at startup
    def __init__(self, user_service: UserService) -> None:
        self.user_service = user_service

    @router.get("/")
    # Request-scoped dependencies must use the Injected[] annotation
    async def get_users(self, request_context: Injected[RequestContext]):
        return self.user_service.find_all()

    @router.post("/")
    async def create_user(self, request: CreateUserRequest):
        return self.user_service.create_user(request)
```

```python title="app/app.py"

# Let Wireup know of all your class-based routes.
wireup.integration.fastapi.setup(
    container, 
    app, 
    class_based_routes=[UsersController]
)
```

### Benefits

1. **Startup-time Dependency Injection**
    * Dependencies in `__init__` are injected once during startup.
    * Significantly better performance compared to per-request injection.

2. **Logical Organization**
    * Group related endpoints into cohesive controllers.
    * Better code navigation and maintenance.

3. **Shared Dependencies**
    * Constructor-injected dependencies are available to all endpoints.
    * Reduces duplicate dependency declarations.

4. **Code Reuse**
    * Share common logic between endpoints in the same controller.
    * Perfect for cross-cutting concerns like validation or authentication.

