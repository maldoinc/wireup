# Injectables

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
| `qualifier` | A unique identifier to distinguish between multiple implementations of the same type. See [Multiple Registrations](multiple_registrations.md). | `None` |
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

!!! tip "Learn More"
    For details on handling resources (e.g. database connections) with generators, see [Factory Functions](factories.md).
