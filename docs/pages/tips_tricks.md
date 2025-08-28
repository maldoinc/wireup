!!! tip "Reduce init boilerplate"

    When building services with multiple dependencies, `__init__` methods may become repetitive.
    Combine the `@service` decorator with Python's `@dataclass` to eliminate initialization boilerplate.


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
                # Simulate loading a large ML model (e.g., 500MB+ model file)
                import pickle
                with open("models/large_recommendation_model.pkl", "rb") as f:
                    return pickle.load(f)
        ```