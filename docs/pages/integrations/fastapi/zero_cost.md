Wireup allows you to achieve real zero-cost runtime dependency injection in FastAPI via class-based routes.
Wireup will create all class-based routes and their dependencies once at startup and completely detach itself
from other runtime behavior.


Wireup class-based routes allow you to define dependencies where the objects are instantiated once on startup.
This results in no overhead when making requests to `GET /users` as there are no dependencies on that method.

## 1. Set up class-based routes

```python title="app/routes/greeter.py"
class UsersController:
    router = fastapi.APIRouter(prefix="/users")

    def __init__(self, user_service: UserService) -> None:
        self.user_service = user_service

    @router.get("/")
    def get_users(self):
        return self.user_service.find_all()
```

## 2. Disable middleware

Wireup by default adds a middleware to the integration for it to properly enter/exit a scope per request as well as
expose the current `fastapi.Request` as a Wireup dependency.

If all your services are singletons, and you don't need the request dependency then you can disable the middleware
altogether.

This results in Wireup only performing injection at startup and be completely detached from runtime behavior.

!!! tip
    If you will need access to transient/scoped dependencies or the fastapi request in Wireup dependencies,
    you can reenable the middleware at any time without it affecting the class-based routes.