# Configuration

Wireup containers can store configuration that can be injected. This enables self-contained
definitions without having to create factories for every injectable.

## Loading Configuration

Configuration is passed to the container during creation as a dictionary. A common pattern is to read from environment variables and map them to known configuration keys.

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

You are not limited to primitives. You can inject entire configuration objects, such as Dataclasses or Pydantic models. This allows you to group related settings and inject only what a service needs.

```python
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    url: str
    max_connections: int

container = wireup.create_sync_container(
    config={"db_config": DatabaseConfig(url="...", max_connections=10)},
    injectables=[...]
)

@injectable
class DatabaseService:
    def __init__(
        self,
        # Inject only the database configuration
        config: Annotated[DatabaseConfig, Inject(config="db_config")]
    ) -> None:
        self.connection = connect(config.url)
```

### Default Values

Wireup uses Python's native default arguments for optional configuration. If a config key is missing and a default value is provided in the `__init__`, Wireup will use the default instead of raising an error.

```python
@injectable
class Server:
    def __init__(
        self,
        # If "PORT" is not in config, 8080 is used
        port: Annotated[int, Inject(config="PORT")] = 8080
    ) -> None:
        self.port = port
```

## Interpolation

You can create dynamic configuration values by interpolating other configuration keys using the `${key}` syntax.

```python
@injectable
class FileStorageService:
    def __init__(
        self,
        # If config is {"env": "prod"}, this becomes "/tmp/uploads/prod"
        upload_path: Annotated[str, Inject(expr="/tmp/uploads/${env}")]
    ) -> None:
        self.upload_path = upload_path
```

!!! note "Expression results are strings"
    Configuration expressions always return strings. Non-string configuration values are converted using `str()` before interpolation.
