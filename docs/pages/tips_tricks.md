!!! tip "Reduce init boilerplate"

    When building services with multiple dependencies, `__init__` methods may become repetitive.
    Combine the `@service` decorator with Python's `@dataclass` to eliminate initialization boilerplate.

    Depending on class definitions some classes may benefit in readability from this more than others. Apply best judgement here.

    === "Before"

        ```python title="services/order_processor.py"
        @service
        class OrderProcessor:
            def __init__(
                self,
                payment_gateway: PaymentGateway,
                inventory_service: InventoryService,
                order_repository: OrderRepository,
            ):
                self.payment_gateway = payment_gateway
                self.inventory_service = inventory_service
                self.order_repository = order_repository
        ```

    === "After"

        ```python title="services/order_processor.py"
        from dataclasses import dataclass

        @service
        @dataclass
        class OrderProcessor:
            payment_gateway: PaymentGateway
            inventory_service: InventoryService
            order_repository: OrderRepository
        ```

    === "Counter-example"

        ```python
        @service
        @dataclass
        class Foo:
            FOO_CONST = 1  # Not added to __init__ by @dataclass.
            logger = logging.getLogger(__name__)  # Not added to __init__ by @dataclass.

            # These will be added to __init__ by @dataclass
            # and marked as dependencies by Wireup.
            payment_gateway: PaymentGateway
            inventory_service: InventoryService
            order_repository: OrderRepository
        ```

        In this example, due to how the `@dataclass` decorator works, combining the two
        leads to code that's more difficult to read, since it's not immediately what are dependencies and what are class fields.

---

!!! tip "Aliased parameters"

    If you don't like having string parameters in your service objects you can alias them instead.

    === "Before"

        ```python
        def list_users(env: Annotated[str, Inject(param="env")]) -> None: ...
        def get_users(env: Annotated[str, Inject(param="env")]) -> None: ...
        ```

    === "After"

        ```python
        EnvParameter = Annotated[str, Inject(param="env")]

        def list_users(env: EnvParameter) -> None: ...
        def get_users(env: EnvParameter) -> None: ...
        ```

---

!!! tip "Eager loading"

    By default, Wireup creates services lazily when they're first requested, but for singleton services that are expensive to create, you can pre-initialize them during application startup to avoid delays and ensure consistent response times when handling requests.

    === "Application Setup"

        ```python title="main.py"
        from wireup import Injected
        import contextlib
        import wireup.integration.fastapi
        import wireup.integration.fastapi import get_app_container
        import wireup

        @contextlib.asynccontextmanager
        async def lifespan(app: FastAPI):
            container = get_app_container(app)
            
            # Pre-initialize expensive singletons during startup
            await container.get(MLModelService)
            
            yield

        container = wireup.create_async_container(...)
        app = FastAPI(lifespan=lifespan)
        wireup.integration.fastapi.setup(container, app)


        @app.post("/users/{user_id}/recommendations")
        async def get_recommendations(
            ml_service: Injected[MLModelService], 
            user_id: str
        ):
            # ML model is already loaded - no delays!
            return ml_service.predict(user_id)
        ```
    
    === "ML Model Service"

        ```python
        import pickle
        from wireup import service

        @service
        class MLModelService:
            """Machine learning model that takes time to load"""
            def __init__(self):
                # Load large model file from disk (expensive operation)
                self.model = self._load_model()
                
            def _load_model(self):
                # Simulate loading a large ML model
                import pickle
                with open("models/large_recommendation_model.pkl", "rb") as f:
                    return pickle.load(f)
        ```

---

!!! tip "Null Object Pattern for Optional Dependencies"

    Instead of adding conditional checks throughout your code, use the pattern to handle
    optional dependencies cleanly. It involves creating a noop implementation
    that can be used when the real implementation is not available.


    ```python title="services/cache.py"
    from wireup import abstract, service
    from typing import Any
    
    class Cache(Protocol):
        def get(self, key: str) -> Any | None: ...
        def set(self, key: str, value: str) -> None: ...

    class RedisCache: ...  # Real Redis implementation

    class NullCache:
        def get(self, key: str) -> Any | None:
            return None  # Always cache miss
        def set(self, key: str, value: str) -> None:
            return None  # Do nothing

    @service
    def cache_factory(
        redis_url: Annotated[str | None, Inject(param="redis_url")],
    ) -> Cache:
        return RedisCache(redis_url) if redis_url else NullCache()
    ```

    **Usage**

    === "Before: Optional Dependencies"

        ```python
        @service
        class UserService:
            def __init__(self, cache: Cache | None):
                self.cache = cache
                
            def get_user(self, user_id: str) -> User:
                # Guard required
                if self.cache and (cached := self.cache.get(f"user:{user_id}")):
                    return User.from_json(cached)
                
                user = self.db.get_user(user_id)
                
                # Guard required
                if self.cache:
                    self.cache.set(f"user:{user_id}", user.to_json())
                
                return user
        ```

    === "After: Null Pattern"

        ```python
        @service
        class UserService:
            def __init__(self, cache: Cache):
                self.cache = cache  # Always a Cache instance
                
            def get_user(self, user_id: str) -> User:
                if cached := self.cache.get(f"user:{user_id}"):
                    return User.from_json(cached)
                
                user = self.db.get_user(user_id) 
                self.cache.set(f"user:{user_id}", user.to_json())
                return user
        ```
