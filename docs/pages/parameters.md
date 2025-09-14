# Configuration Parameters

Wireup containers can store configuration parameters that services can inject. This enables self-contained service
definition without having to create factories for every service.

## Setting up parameters

When creating a container, provide a dictionary of configuration parameters.

```python
import wireup

container = wireup.create_sync_container(
    parameters={
        "database_url": "postgresql://localhost:5432/app",
        "env": "production",
        "debug_mode": True,
        "max_connections": 100,
        "allowed_hosts": ["localhost", "example.com"]
    }
)
```

## Injecting parameters

### By name

Inject a specific parameter by name using `Inject(param="parameter_name")`:

```python
from typing import Annotated
from wireup import service, Inject

@service
class DatabaseService:
    def __init__(
        self,
        url: Annotated[str, Inject(param="database_url")],
        max_connections: Annotated[int, Inject(param="max_connections")]
    ) -> None:
        self.url = url
        self.max_connections = max_connections
```

### Using expressions

Create dynamic configuration values by interpolating parameters using `${parameter_name}` syntax:

```python
@service
class FileStorageService:
    def __init__(
        self, 
        upload_path: Annotated[str, Inject(expr="/tmp/uploads/${env}")]
    ) -> None:
        # upload_path = "/tmp/uploads/production"
        self.upload_path = upload_path
```

!!! note "Expression results are strings"
    Parameter expressions always return strings. Non-string parameters are converted using `str()` before interpolation.

For more complex configuration scenarios or to keep domain objects free of annotations, see the [Annotation-Free Architecture](annotation_free.md#configuration-classes) guide.
