An injectable is any class or function that you register with the container, making it available to be requested as a
dependency. Once registered, Wireup can instantiate it, resolve its own dependencies, and inject it wherever needed.

## The `@injectable` Decorator

The `@injectable` decorator marks a class or function for registration with the container.

=== "Classes"

    ```python
    from wireup import injectable


    @injectable
    class UserRepository: ...
    ```

=== "Functions"

    ```python
    from wireup import injectable


    @injectable
    def db_connection() -> DatabaseConnection: ...
    ```

### Arguments

You can customize how an injectable is registered by passing arguments to the decorator:

| Argument    | Description                                                                                                           | Default       |
| :---------- | :-------------------------------------------------------------------------------------------------------------------- | :------------ |
| `lifetime`  | Controls how long the object lives (e.g., `"singleton"`, `"scoped"`). See [Lifetimes](lifetimes_and_scopes.md).       | `"singleton"` |
| `qualifier` | A unique identifier, useful when you have multiple implementations of the same type. See [Interfaces](interfaces.md). | `None`        |
| `as_type`   | Register the object as a different type (like a Protocol or Base Class). See [Interfaces](interfaces.md).             | `None`        |

```python
from wireup import injectable


@injectable(lifetime="scoped", qualifier="readonly")
class DbSession: ...
```

## Defining Dependencies

Wireup resolves dependencies using **Type Hints**. It inspects the types you declare and automatically finds the
matching injectable.

### Classes

Standard Python classes with type-hinted `__init__` methods are automatically wired. No extra configuration is needed.

```python
from wireup import injectable


@injectable
class UserService:
    # UserRepository will be injected automatically
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo
```

### Factories

Functions can be registered as factories. This is standard for creating 3rd-party objects, when complex setup is
required or for enforcing clean architecture.

See [Factories](factories.md) and [Resource Management](resources.md).

```python
import boto3
from wireup import injectable, Inject
from typing import Annotated


@injectable
def create_s3_client(
    region: Annotated[str, Inject(config="aws_region")],
) -> boto3.client:
    return boto3.client("s3", region_name=region)
```

### Dataclasses

You can combine `@injectable` with `@dataclass` to eliminate `__init__` boilerplate.

=== "Standard Class"

    ```python
    @injectable
    class OrderProcessor:
        def __init__(
            self,
            payment_gateway: PaymentGateway,
            inventory_service: InventoryService,
        ):
            self.payment_gateway = payment_gateway
            self.inventory_service = inventory_service
    ```

=== "Dataclass"

    ```python
    from dataclasses import dataclass


    @injectable
    @dataclass
    class OrderProcessor:
        payment_gateway: PaymentGateway
        inventory_service: InventoryService
    ```

??? warning "Counter-example"

    Mix with caution if your class has many non-dependency fields.

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

    In this example, due to how the `@dataclass` decorator works, combining the two leads to code that's more difficult to
    read, since it's not immediately obvious what are dependencies and what are class fields.

## Dependencies with Default Values

When Wireup encounters a dependency it doesn't recognize, it normally raises an error. However, if that parameter has a
**default value**, Wireup will skip it and let Python use the default instead.

This is useful when integrating with libraries that add their own `__init__` parameters, such as Pydantic Settings:

```python
from pydantic_settings import BaseSettings
from wireup import injectable


@injectable
class Settings(BaseSettings):
    app_name: str = "myapp"
    debug: bool = False
```

In this example, Pydantic's `BaseSettings` adds parameters that Wireup doesn't manage. Since they have defaults, Wireup
allows the class to be registered without errors.

!!! note

    This only applies to parameters with explicit default values. Parameters without defaults that reference unknown types
    will still raise an error to catch configuration mistakes early.

## Next Steps

- [Configuration](configuration.md) - Inject configuration values.
- [Lifetimes & Scopes](lifetimes_and_scopes.md) - Control how long objects live.
- [Factories](factories.md) - Advanced creation logic.
