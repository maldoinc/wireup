Class-Based Routes powered by Wireup allow you to have real singleton routers in FastAPI.

These class-based routes (or controllers as commonly known), are regular classes that can define their dependencies
in `__init__` *or* in the route handler method.

## Requirements

* The class must have a field called `router` of type `fastapi.APIRoute`. This is a regular fastapi router that
you can use as usual.
* The routers must not be registered with fastapi but instead registered with Wireup by passing them to the
`wireup.integration.fastapi.setup` method.



```python title="app/routes/greeter.py"
class UsersController: # (1)!
    router = fastapi.APIRouter(prefix="/users") # (2)!

    def __init__(self, user_service: UserService) -> None: # (3)!
        self.user_service = user_service

    @router.get("/")
    def get_users(self, request_context: Injected[RequestContext]): # (4)!
        return self.user_service.find_all()

    @router.post("/")
    def create_user(self, request: CreateUserRequest):
        new_user = self.user_service.create_user(...)
```

1. Define a class-based router.
2. Instantiate a regular fastapi router in the class and use this to decorate your endpoints just like you normally would.
3. Define shared dependencies in the initializer. These are injected only once during application startup.
4. If you need request/transient scoped dependencies you can request them in the endpoint as usual.
**Note**: In route handlers, you need to annotate Wireup dependencies with Injected like in any other route.

## Advantages of Class-Based Routes

**Zero-cost runtime injection**

They are instantiated by Wireup **once** and handle requests during the entire lifetime of the application. You pay the cost for the dependencies in the init only once at application startup. Normally with fastapi or other libraries that offer
similar functionality, the route handler gets created on every request.

**Group related endpoints**

For example, all endpoints related to "users" can be placed in a UserController, making the codebase more organized and easier to navigate.

**Dependency Sharing**

Controllers can share dependencies (e.g., services, repositories) across multiple endpoints within the same controller. This avoids repetitive dependency injection in each function and promotes DRY (Don't Repeat Yourself) principles.

**Reusability**

By grouping endpoints into controllers, shared logic (e.g., authentication, validation) can be reused across multiple methods within the same controller.

