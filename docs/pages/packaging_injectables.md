Use this guide when you want to package and distribute injectables across applications, teams, or internal
libraries. Wireup always receives a list of injectables, so the main choice is how your package exposes that
list.

## 1. Export A Module Or Package

Use this when the injectables are fixed and the application does not need to choose between variants. 
Wireup's own integrations use the same idea. For example, `wireup.integration.fastapi` is a module with injectables that can be passed directly in `injectables=[...]` and exposes FastAPI `Request`, `WebSocket`, and `WireupTask`.

Example:

```python title="team_name_sqlalchemy/__init__.py"
@injectable
def database_session() -> DatabaseSession: ...


@injectable
class UserRepository: ...
```

```python title="app.py"
import wireup
import team_name_sqlalchemy


container = wireup.create_sync_container(
    injectables=[team_name_sqlalchemy],
)
```

This is the simplest option. It works well for internal packages and libraries with a single default setup.

## 2. Export A List Of Injectables

Use this when you want the package to export an explicit list of injectables instead of relying on module
scanning.

```python title="team_name_sqlalchemy/__init__.py"
@injectable
def database_session() -> DatabaseSession: ...


@injectable
class UserRepository: ...


INJECTABLES = [database_session, UserRepository]
```

```python title="app.py"
import wireup
import team_name_sqlalchemy


container = wireup.create_sync_container(
    injectables=[*team_name_sqlalchemy.INJECTABLES],
)
```

## 3. Export A Function That Returns Injectables

Use this when the package exposes parameters of its own, such as backend choices or feature flags.

```python title="team_name_sqlalchemy/__init__.py"
from typing import Literal, Protocol

from wireup import injectable


class Cache(Protocol): ...


@injectable(as_type=Cache)
class RedisCache: ...


@injectable(as_type=Cache)
class MemcachedCache: ...


def make_injectables(
    *,
    backend: Literal["redis", "memcached"],
) -> list[object]:
    if backend == "redis":
        return [RedisCache]

    return [MemcachedCache]
```

```python title="app.py"
import wireup
from team_name_sqlalchemy import make_injectables


container = wireup.create_sync_container(
    injectables=[*make_injectables(backend=settings.cache_backend)],
)
```

For reusable provider-style bundles or registering the same subgraph more than once, see
[Reusable Bundles](reusable_bundles.md).

## Which One Should You Pick?

- Use a module when the package has one setup and consumers do not need to choose between variants.
- Use a list when you want explicit control over what gets registered without module scanning.
- Use a function when the package exposes parameters that consumers must provide when building the injectables.
