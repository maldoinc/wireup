Wireup containers can store configuration that can be injected. This enables self-contained
definitions without having to create factories for every injectable.

## Setting up configuration

When creating a container, provide a dictionary with configuration.

```python
import wireup

container = wireup.create_sync_container(
    config={
        "database_url": "postgresql://localhost:5432/app",
        "env": "production",
        "debug_mode": True,
        "max_connections": 100,
        "allowed_hosts": ["localhost", "example.com"]
    }
)
```

## Injecting configuration
### By key

Inject a specific configuration by key using `Inject(config="config_key")`:

```python
from typing import Annotated
from wireup import injectable, Inject

@injectable
class DatabaseService:
    def __init__(
        self,
        url: Annotated[str, Inject(config="database_url")],
        max_connections: Annotated[int, Inject(config="max_connections")]
    ) -> None:
        self.url = url
        self.max_connections = max_connections
```

### Using expressions

Create dynamic configuration values by interpolating configuration using `${config_key}` syntax:

```python
@injectable
class FileStorageService:
    def __init__(
        self, 
        upload_path: Annotated[str, Inject(expr="/tmp/uploads/${env}")]
    ) -> None:
        # upload_path = "/tmp/uploads/production"
        self.upload_path = upload_path
```

!!! note "Expression results are strings"
    Configuration expressions always return strings. Non-string configuration values are converted using `str()` before interpolation.

For more complex configuration scenarios or to keep domain objects free of annotations, see the [Annotation-Free Architecture](annotation_free.md#configuration-classes) guide.
