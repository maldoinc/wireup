Wireup containers can store and inject configuration. This enables self-contained definitions without having to create
factories for every injectable.

## Loading Configuration

Configuration is passed to the container during creation as a dictionary.

```python
import wireup
import os

container = wireup.create_sync_container(
    config={
        "database_url": os.environ["DB_CONNECTION_STRING"],
        "env": os.environ.get("APP_ENV", "production"),
        "max_connections": 100,
    }
)
```

## Injecting Configuration

### Primitives (Key-Value)

Inject specific values by key using `Inject(config="key")`.

```python
from typing import Annotated
from wireup import injectable, Inject


@injectable
class DatabaseService:
    def __init__(
        self,
        # Injects the value of "database_url" from the config dict
        url: Annotated[str, Inject(config="database_url")],
    ) -> None:
        self.url = url
```

### Structured Objects

You are not limited to primitives. You can inject entire configuration objects, such as Dataclasses or Pydantic models.
This allows you to group related settings and inject only what a service needs.

=== "Dataclass"

    ```python
    from dataclasses import dataclass


    @dataclass
    class DatabaseConfig:
        url: str
        max_connections: int


    container = wireup.create_sync_container(
        config={"db_config": DatabaseConfig(url="...", max_connections=10)},
        injectables=[...],
    )
    ```

=== "Pydantic"

    ```python
    from pydantic_settings import BaseSettings


    class DatabaseSettings(BaseSettings):
        url: str
        max_connections: int = 10


    container = wireup.create_sync_container(
        config={"db": DatabaseSettings()},  # Loads from env automatically
        injectables=[...],
    )
    ```

Then inject the configuration object:

```python
import sqlite3


@injectable
class DatabaseService:
    def __init__(
        self, config: Annotated[DatabaseConfig, Inject(config="db_config")]
    ) -> None:
        self.connection = sqlite3.connect(config.url)
```

## Interpolation

You can create dynamic configuration values by interpolating other configuration keys using the `${key}` syntax.

```python
# config = {"env": "prod", "host": "localhost", "port": 5432}


@injectable
class FileStorageService:
    def __init__(
        self,
        # Becomes "/tmp/uploads/prod"
        upload_path: Annotated[str, Inject(expr="/tmp/uploads/${env}")],
        # Becomes "postgresql://localhost:5432/mydb"
        db_url: Annotated[
            str, Inject(expr="postgresql://${host}:${port}/mydb")
        ],
    ) -> None:
        self.upload_path = upload_path
```

!!! note "Expression results are strings"

    Configuration expressions always return strings. Non-string configuration values are converted using `str()` before
    interpolation.

## Aliasing Configuration Keys

Avoid repeating string keys across your codebase by creating type aliases. This also makes refactoring easier if
configuration keys change.

```python
# Create an alias for the configuration injection
EnvConfig = Annotated[str, Inject(config="env")]


# Use the alias instead of repeating Inject(config="env")
def list_users(env: EnvConfig) -> None: ...
def get_users(env: EnvConfig) -> None: ...
```

## Next Steps

- [Lifetimes & Scopes](lifetimes_and_scopes.md) - Control how long objects live.
- [Factories](factories.md) - Create complex dependencies and third-party objects.
- [Testing](testing.md) - Override configuration values for testing.
