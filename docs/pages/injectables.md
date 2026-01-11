An injectable is any class or function that Wireup manages. They are the building blocks of your application.

## The `@injectable` Decorator

To register a class or function as an injectable, decorate it with `@injectable`.

```python
from wireup import injectable

@injectable
class UserRepository: ...

@injectable
def db_connection() -> DatabaseConnection: ...
```

### Arguments

The decorator accepts arguments to control how the injectable is registered:

| Argument | Description | Default |
| :--- | :--- | :--- |
| `lifetime` | Controls the lifespan of the object (e.g. `"singleton"`, `"scoped"`). See [Lifetimes](lifetimes_and_scopes.md). | `"singleton"` |
| `qualifier` | A unique identifier to distinguish between multiple implementations of the same type. See [Interfaces](interfaces.md). | `None` |
| `as_type` | Register the injectable as a different type (e.g., a Protocol or ABC). See [Interfaces](interfaces.md). | `None` |

```python
from wireup import injectable

@injectable(lifetime="scoped", qualifier="readonly")
class DbSession: ...
```

## Defining Injectables

Wireup resolves dependencies based on type hints in the `__init__` method for classes, or the function signature for factories.

### Classes

Use standard Python classes and type hints.

```python
@injectable
class UserService:
    # UserRepository will be injected automatically
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo
```

### Factories

Functions can also be registered as injectables. This is useful for creating objects that you don't control (like 3rd party libraries) or that require complex setup.

```python
import boto3
from wireup import injectable, Inject
from typing import Annotated

@injectable
def create_s3_client(
    region: Annotated[str, Inject(config="aws_region")]
) -> boto3.client:
    return boto3.client("s3", region_name=region)
```

!!! tip "Reduce init boilerplate"

    When building injectables with multiple dependencies, `__init__` methods may become repetitive.
    Combine the `@injectable` decorator with Python's `@dataclass` to eliminate initialization boilerplate.

    Depending on class definitions some classes may benefit in readability from this more than others. Apply best judgement here.

    === "Before"

        ```python title="services/order_processor.py"
        @injectable
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

        @injectable
        @dataclass
        class OrderProcessor:
            payment_gateway: PaymentGateway
            inventory_service: InventoryService
            order_repository: OrderRepository
        ```

    === "Counter-example"

        ```python
        @injectable
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

## Next Steps

* [Configuration](configuration.md) - Inject configuration values from environment variables or structured objects.
* [Lifetimes & Scopes](lifetimes_and_scopes.md) - Control singleton, scoped, and transient lifetimes.
* [Factories](factories.md) - Advanced patterns for creating complex injectables.
