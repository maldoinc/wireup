# Parameters

Wireup containers can store configuration parameters that your services can inject. This enables clean, self-contained service declarations with explicit configuration dependencies.

!!! warning "Parameters are for configuration only"
    Parameters should only be used for application configuration such as environment names, database URLs, API keys, and other settings.
    
    **Do not** use parameters to pass runtime data or as a global session store.

## Setting up parameters

When creating a container, provide a dictionary of configuration parameters:

```python
import wireup

container = wireup.create_sync_container(
    parameters={
        "cache_dir": "/tmp/cache",
        "env": "production", 
        "gh_api_key": "your_github_api_key_here",
        "redis_url": "redis://localhost:6379"
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
class GithubClient:
    def __init__(self, api_key: Annotated[str, Inject(param="gh_api_key")]) -> None:
        self.api_key = api_key

@service  
class CacheService:
    def __init__(self, redis_url: Annotated[str, Inject(param="redis_url")]) -> None:
        self.redis_url = redis_url
```

### Using expressions

Create dynamic configuration values by interpolating multiple parameters using the `${parameter_name}` syntax:

```python
@service
class LogManager:
    def __init__(self, logs_dir: Annotated[str, Inject(expr="${cache_dir}/${env}/logs")]) -> None:
        # With the parameters above, logs_dir becomes "/tmp/cache/production/logs"
        self.logs_dir = logs_dir
```

!!! note "Expression results are strings"
    Parameter expressions always return strings. Non-string parameters are converted using `str()`.

## Alternative: Class-based configuration

Wireup's parameter configuration is optional. You can use typed classes for configuration, supported via factories.

Register your settings as a service and inject them into factories like regular dependencies.

See [Use Without Annotations](use_without_annotations.md) for more details on factory-based configuration patterns.