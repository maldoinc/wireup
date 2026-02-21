Use factories to handle complex creation logic, instantiate third-party classes, or manage resources that can't be
handled by simple class constructors.

## Third-party Classes

You can't add `@injectable` to code you don't own. Factories solve this by wrapping third-party classes in a function
you control. The factory creates and configures the object, and Wireup registers it by the return type.

**Example: Redis Client**

```python
from typing import Annotated

import redis
from wireup import Inject, injectable


@injectable
def redis_factory(
    url: Annotated[str, Inject(config="redis_url")],
) -> redis.Redis:
    return redis.from_url(url)


# Usage:
@injectable
class AuthService:
    def __init__(self, cache: redis.Redis):
        self.cache = cache
```

## Pure Domain Objects

If you prefer to keep your domain layer free of Wireup imports, don't use `@injectable` on those classes. Instead,
create factory functions in a separate wiring module that construct and return them.

```python title="domain/services.py"
# No Wireup imports here
class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository
```

```python title="wiring/factories.py"
from wireup import injectable
from domain.services import UserService


@injectable
def user_service_factory(repository: UserRepository) -> UserService:
    return UserService(repository)
```

## Complex Initialization

Some objects need conditional logic, multi-step setup, or configuration that depends on the environment. Factories let
you encapsulate this logic in one place rather than scattering it across your codebase.

```python
from wireup import injectable


@injectable
def db_connection_factory(config: AppConfig) -> DatabaseConnection:
    timeout = config.timeout if config.is_production else 30

    conn = DatabaseConnection(dsn=config.dsn, timeout=timeout)
    conn.set_encoding("utf-8")

    return conn
```

## Injecting Primitives

If you register two factories that both return `str`, Wireup can't tell them apart. Use `typing.NewType` to create
distinct types so each primitive can be requested independently.

```python title="factories.py"
from typing import NewType
from wireup import injectable

AuthenticatedUsername = NewType("AuthenticatedUsername", str)


@injectable(lifetime="scoped")
def authenticated_username_factory(auth: AuthService) -> AuthenticatedUsername:
    user = auth.get_current_user()
    return AuthenticatedUsername(user.username)
```

Usage:

```python
from wireup import injectable


@injectable(lifetime="scoped")
class UserProfileService:
    def __init__(self, username: AuthenticatedUsername):
        self.username = username
```

## Strategy Pattern

When the correct implementation depends on runtime state (user preferences, feature flags, environment), a factory can
inspect other dependencies and return the appropriate one.

```python
from typing import Protocol
from wireup import injectable


class Notifier(Protocol):
    def notify(self, message: str): ...


@injectable(lifetime="scoped")
def get_user_notifier(
    user: AuthenticatedUser,
    slack: SlackNotifier,
    email: EmailNotifier,
) -> Notifier:
    if user.prefers_slack:
        return slack

    return email
```

## Models and DTOs

Sometimes you want to inject data that comes from another service, like the currently authenticated user. A factory can
call that service and return the result, making it available as a dependency.

```python
from wireup import injectable


@injectable(lifetime="scoped")
def get_current_user(auth_service: AuthService) -> AuthenticatedUser:
    return auth_service.get_current_user()
```

## Optional Dependencies

Some dependencies are only available under certain conditions, like a cache that's disabled in development. Factories
can return `None` to signal the dependency isn't available, and consumers can handle this gracefully.

!!! important "Registration Required"

    The factory **must still be registered** even if it returns `None`. Wireup needs to know *how* to resolve the specific
    type, even if the result is nothing.

```python
from wireup import injectable


@injectable
def cache_factory(settings: Settings) -> Redis | None:
    if not settings.use_cache:
        return None

    return Redis.from_url(settings.redis_url)
```

**Requesting Optional Dependencies**

```python
from wireup import injectable


@injectable
class UserService:
    # Use T | None (Python 3.10+) or Optional[T]
    def __init__(self, cache: Redis | None) -> None:
        self.cache = cache

    def get(self, user_id: str):
        if self.cache:
            return self.cache.get(user_id)
        # ...
```

??? tip "Null Object Pattern for Optional Dependencies"

    Instead of adding conditional checks throughout your code, use the pattern to handle optional dependencies cleanly. It
    involves creating a noop implementation that can be used when the real implementation is not available.

    ```python title="services/cache.py"
    from typing import Annotated, Any, Protocol
    from wireup import Inject, injectable


    class Cache(Protocol):
        def get(self, key: str) -> Any | None: ...
        def set(self, key: str, value: str) -> None: ...


    class RedisCache: ...  # Real Redis implementation


    class NullCache:
        def get(self, key: str) -> Any | None:
            return None  # Always cache miss

        def set(self, key: str, value: str) -> None:
            return None  # Do nothing


    @injectable
    def cache_factory(
        redis_url: Annotated[str | None, Inject(config="redis_url")],
    ) -> Cache:
        return RedisCache(redis_url) if redis_url else NullCache()
    ```

    **Usage**

    === "Before: Optional Dependencies"

        ```python
        @injectable
        class UserService:
            def __init__(self, cache: Cache | None):
                self.cache = cache

            def get_user(self, user_id: str) -> User:
                # Guard required
                if self.cache and (cached := self.cache.get(f"user:{user_id}")):
                    return User.from_json(cached)

                user = self.db.get_user(user_id)

                # Guard required
                if self.cache:
                    self.cache.set(f"user:{user_id}", user.to_json())

                return user
        ```

    === "After: Null Pattern"

        ```python
        @injectable
        class UserService:
            def __init__(self, cache: Cache):
                self.cache = cache  # Always a Cache instance

            def get_user(self, user_id: str) -> User:
                if cached := self.cache.get(f"user:{user_id}"):
                    return User.from_json(cached)

                user = self.db.get_user(user_id)
                self.cache.set(f"user:{user_id}", user.to_json())
                return user
        ```

## Reusable Factory Bundles

When you need to register the same dependency graph multiple times with different runtime settings, use a parameterized
function that returns injectable factories.

This is useful for cases like:

* Multiple database clients with different connection settings.
* Tenant-specific integrations.
* Reusing the same wiring pattern across environments.

```python
from typing import Annotated
import wireup
from wireup import Inject, injectable


class DbClient: ...


class DbRepository: ...


def make_db_bundle(*, dsn: str, qualifier: str | None = None) -> list[object]:
    @injectable(qualifier=qualifier)
    def db_client_factory() -> DbClient:
        return DbClient(dsn=dsn)

    @injectable(qualifier=qualifier)
    def db_repo_factory(
        client: Annotated[DbClient, Inject(qualifier=qualifier)],
    ) -> DbRepository:
        return DbRepository(client=client)

    return [db_client_factory, db_repo_factory]


primary = make_db_bundle(dsn="postgresql://primary-db")
analytics = make_db_bundle(
    dsn="postgresql://analytics-db", qualifier="analytics"
)

container = wireup.create_sync_container(
    injectables=[*primary, *analytics, app.services],
)
```

Use an unqualified default (`None`) for your primary bundle, then add qualifiers only where needed:

```python
from typing import Annotated
from wireup import Inject, Injected, injectable


@injectable
class ReportService:
    def __init__(
        self,
        primary_repo: Injected[DbRepository],
        analytics_repo: Annotated[DbRepository, Inject(qualifier="analytics")],
    ) -> None:
        self.primary_repo = primary_repo
        self.analytics_repo = analytics_repo
```
