Performant, concise and type-safe Dependency Injection for Python.

[![GitHub](https://img.shields.io/github/license/maldoinc/wireup)](https://github.com/maldoinc/wireup)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup)](https://pypi.org/project/wireup/)
[![PyPI - Version](https://img.shields.io/pypi/v/wireup)](https://pypi.org/project/wireup/)

Automate dependency management using Python's type system. Build complex applications with native support for async and
generators, plus integrations for popular frameworks out of the box.

!!! tip "Zero Runtime Overhead"

    **New**: Inject Dependencies in FastAPI with zero runtime overhead using
    [Class-Based Handlers](integrations/fastapi/class_based_handlers.md).

### ⚡ Clean & Type-Safe DI

Use decorators and annotations for concise, co-located definitions, or factories to keep your domain model pure and
decoupled.

=== "1. Basic Usage"

    Start simple. Register classes directly using decorators and let the container resolve dependencies automatically.

    ```python hl_lines="5 11 13"
    from wireup import injectable, create_sync_container
    from sqlalchemy import create_engine


    @injectable
    class Database:
        def __init__(self) -> None:
            self.engine = create_engine("sqlite://")


    @injectable
    class UserService:
        def __init__(self, db: Database) -> None:
            self.db = db


    # Now that the dependencies are defined, register them with the container.
    # You can pass a list of classes, functions, or even modules to be scanned.
    container = create_sync_container(injectables=[Database, UserService])
    user_service = container.get(UserService)  # ✅ Dependencies resolved.
    ```

=== "2. Inject Configuration"

    Seamlessly inject configuration alongside other dependencies, eliminating the need for manually wiring them up via
    factories.

    ```python hl_lines="7 10 14 16"
    from wireup import injectable, create_sync_container, Inject
    from typing import Annotated
    import os
    from sqlalchemy import create_engine


    @injectable
    class Database:
        # Inject "db_url" from the container configuration.
        def __init__(self, url: Annotated[str, Inject(config="db_url")]) -> None:
            self.engine = create_engine(url)


    @injectable
    class UserService:
        def __init__(self, db: Database) -> None:
            self.db = db


    container = create_sync_container(
        injectables=[Database, UserService], config={"db_url": os.environ["DB_URL"]}
    )
    user_service = container.get(UserService)  # ✅ Dependencies resolved.
    ```

=== "3. Clean Architecture"

    Need strict boundaries? Use factories to wire pure domain objects and integrate external libraries like Pydantic.

    ```python title="Domain Layer"
    from pydantic import BaseModel
    from sqlalchemy import create_engine


    # 1. No Wireup imports
    class Database:
        def __init__(self, url: str) -> None:
            self.engine = create_engine(url)


    # 2. Configuration (Pydantic)
    class Settings(BaseModel):
        db_url: str = "sqlite://"
    ```

    ```python title="Wiring" hl_lines="5 10 11"
    from wireup import injectable, create_sync_container


    # 3. Wireup factories
    @injectable
    def make_settings() -> Settings:
        return Settings()


    @injectable
    def make_database(settings: Settings) -> Database:
        return Database(url=settings.db_url)


    container = create_sync_container(injectables=[make_settings, make_database])
    database = container.get(Database)  # ✅ Dependencies resolved.
    ```

### 🎯 Function Injection

Inject dependencies directly into any function. This is useful for CLI commands, background tasks, event handlers, or
any standalone function that needs access to the container.

```python
from wireup import inject_from_container, Injected


@inject_from_container(container)
def migrate_database(db: Injected[Database], settings: Injected[Settings]):
    # ✅ Database and Settings injected.
    pass
```

### 📝 Interfaces & Abstractions

Define abstract types and have the container automatically inject the implementation.

```python
from wireup import injectable, create_sync_container
from typing import Protocol


class Notifier(Protocol):
    def notify(self) -> None: ...


@injectable(as_type=Notifier)
class SlackNotifier:
    def notify(self) -> None: ...


container = create_sync_container(injectables=[SlackNotifier])
notifier = container.get(Notifier)  # ✅ SlackNotifier instance.
```

### 🔄 Managed Lifetimes

Declare dependencies as singletons, scoped, or transient to control whether to inject a fresh copy or reuse existing
instances.

=== "Singleton"

    One instance per application. `@injectable(lifetime="singleton")` is the default.

    ```python
    @injectable
    class Database:
        pass
    ```

=== "Scoped"

    One instance per scope/request, shared within that scope/request.

    ```python
    @injectable(lifetime="scoped")
    class RequestContext:
        def __init__(self) -> None:
            self.request_id = uuid4()
    ```

=== "Transient"

    When full isolation and clean state is required. Every request to create transient services results in a new instance.

    ```python
    @injectable(lifetime="transient")
    class OrderProcessor:
        pass
    ```

### 🏭 Flexible Creation Patterns

Defer instantiation to specialized factories when complex initialization or cleanup is required. Full support for async
and generators. Wireup handles cleanup at the correct time depending on the injectable lifetime.

=== "Synchronous"

    ```python
    class WeatherClient:
        def __init__(self, client: requests.Session) -> None:
            self.client = client


    @service
    def weather_client_factory() -> Iterator[WeatherClient]:
        with requests.Session() as session:
            yield WeatherClient(client=session)
    ```

=== "Async"

    ```python
    class WeatherClient:
        def __init__(self, client: aiohttp.ClientSession) -> None:
            self.client = client


    @service
    async def weather_client_factory() -> AsyncIterator[WeatherClient]:
        async with aiohttp.ClientSession() as session:
            yield WeatherClient(client=session)
    ```

### ❓ Optional Dependencies

Wireup has first-class support for `Optional[T]` and `T | None`. Expose optional dependencies and let Wireup handle the
rest.

```python
@injectable
def make_cache(settings: Settings) -> RedisCache | None:
    return RedisCache(settings.redis_url) if settings.cache_enabled else None


@injectable
class UserService:
    def __init__(self, cache: RedisCache | None):
        self.cache = cache


# You can also retrieve optional dependencies directly
cache = container.get(RedisCache | None)
```

### 🛡️ Improved Safety

Wireup is mypy strict compliant and will not introduce type errors. It will also warn at the earliest possible stage
about configuration errors to avoid surprises at runtime.

=== "Container Creation"

    The container will raise errors at creation time about missing dependencies or other issues.

    ```python
    from wireup import injectable


    @injectable
    class Foo:
        def __init__(self, unknown: NotManagedByWireup) -> None: ...


    container = wireup.create_sync_container(injectables=[Foo])
    # ❌ Parameter 'unknown' of 'Foo' depends on an unknown injectable 'NotManagedByWireup'.
    ```

=== "Function Injection"

    Injected functions will raise errors at module import time rather than when called.

    ```python
    from wireup import inject_from_container, Injected


    @inject_from_container(container)
    def my_function(oops: Injected[NotManagedByWireup]): ...


    # ❌ Parameter 'oops' of 'my_function' depends on an unknown injectable 'NotManagedByWireup'.
    ```

=== "Integrations"

    Wireup integrations assert that requested injections in the framework are valid.

    ```python
    from wireup import Injected
    from fastapi import FastAPI

    app = FastAPI()


    @app.get("/")
    def home(foo: Injected[NotManagedByWireup]): ...


    wireup.integration.fastapi.setup(container, app)
    # ❌ Parameter 'foo' of 'home' depends on an unknown injectable 'NotManagedByWireup'.
    ```

=== "Configuration Checks"

    Configuration injection is also checked for validity.

    ```python
    from wireup import Inject, injectable
    from typing import Annotated


    @injectable
    class Database:
        def __init__(self, url: Annotated[str, Inject(config="db_url")]) -> None:
            self.url = url


    # ❌ Parameter 'url' of Type 'Database' depends on an unknown Wireup config key 'db_url'.
    ```

### 📍 Framework Independent

With Wireup, business logic is decoupled from your runtime. Define injectables once and reuse them across Web
Applications, CLI Tools, and Task Queues without duplication or refactoring.

```python
# 1. Define your Service Layer once (e.g. in my_app.services)
# injectables = [UserService, Database, ...]


# 2. Run in FastAPI
@app.get("/")
@inject_from_container(container)
async def view(service: Injected[UserService]): ...


# 3. Run in CLI
@click.command()
@inject_from_container(container)
def command(service: Injected[UserService]): ...


# 4. Run in Workers (Celery)
@app.task
@inject_from_container(container)
def task(service: Injected[UserService]): ...
```

```mermaid
graph LR
    subgraph "Core Business Logic"
        Services[Injectables & Services]
        Domain[Domain Models]
    end

    subgraph "Entry Points"
        API[FastAPI / Web]
        CLI[Click / CLI]
        Worker[Celery / Worker]
    end

    API -->|Injects| Services
    CLI -->|Injects| Services
    Worker -->|Injects| Services
    
    Services --> Domain
```

### 🔌 Native Integration with popular frameworks

Integrate with popular frameworks for a smoother developer experience. Integrations manage request scopes, injection in
endpoints, and dependency lifetimes.

```python title="Full FastAPI example"
from wireup import injectable, create_async_container, Injected
from fastapi import FastAPI

app = FastAPI()
container = create_async_container(injectables=[UserService, Database])


@app.get("/")
def users_list(user_service: Injected[UserService]):
    pass


wireup.integration.fastapi.setup(container, app)
```

[View all integrations →](integrations/index.md)

### 🧪 Simplified Testing

Wireup decorators only collect metadata. Injectables remain plain classes or functions with no added magic to them. Test
them directly with mocks or fakes, no special setup required.

```python
def test_user_repository():
    fake_db = FakeDatabase()
    repo = UserRepository(db=fake_db)  # Just instantiate directly.
    assert repo.get_user(1) == expected_user
```

You can also use `container.override` to swap dependencies during tests:

```python
with container.override.injectable(target=Database, new=in_memory_database):
    # The /users endpoint depends on Database.
    # During the lifetime of this context manager, requests to inject `Database`
    # will result in `in_memory_database` being injected instead.
    response = client.get("/users")
```

## 📦 Installation

```bash
pip install wireup
```

### Next Steps

- [Getting Started](getting_started.md) - Follow the Getting Started guide for a more in-depth tutorial.
- [Injectables](injectables.md)
- [Configuration](configuration.md)
