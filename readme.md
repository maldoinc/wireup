<div align="center">
<h1>Wireup</h1>
<p>
Type-driven dependency injection for Python. Wireup is battle-tested in production, thread-safe, no-GIL (PEP 703) ready, and designed to fail fast: <strong>if the container starts, it works</strong>.
</p>

[![GitHub](https://img.shields.io/github/license/maldoinc/wireup)](https://github.com/maldoinc/wireup)
[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/maldoinc/wireup/run_all.yml)](https://github.com/maldoinc/wireup)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup)](https://pypi.org/project/wireup/)
[![PyPI - Version](https://img.shields.io/pypi/v/wireup)](https://pypi.org/project/wireup/)
<br />
[![Documentation](https://img.shields.io/badge/%F0%9F%93%9A%20-Documentation-3D9970)](https://maldoinc.github.io/wireup)
[![Documentation](https://img.shields.io/badge/%E2%AD%90-Enjoying%20Wireup%3F%20Star%20on%20GitHub-3D9970)](https://maldoinc.github.io/wireup)

</div>


## Why Wireup?

- **Correct by default**: Wireup catches missing dependencies, circular references, lifetime mismatches, duplicate registrations, and missing config keys at startup. Shared dependencies are created in a thread-safe way.
- **Define once, inject anywhere**: reuse the same service layer in APIs, CLIs, workers, and scripts.
- **Framework-ready**: native integrations for **FastAPI**, **Flask**, **Django**, **Starlette**, **AIOHTTP**, **Click**, **Typer**, and **Strawberry**. [See Integrations](https://maldoinc.github.io/wireup/latest/integrations).
- **Startup-resolved constructor injection for [FastAPI](https://maldoinc.github.io/wireup/latest/integrations/fastapi/class_based_handlers/) and [AIOHTTP](https://maldoinc.github.io/wireup/latest/integrations/aiohttp/class_based_handlers/) handlers**: constructor dependencies are resolved once at startup, not per request. [FastAPI class-based handlers](https://maldoinc.github.io/wireup/latest/integrations/fastapi/class_based_handlers/).
- **Test overrides with context managers**: replace any injectable for a test scope and restore automatically. [See testing docs](https://maldoinc.github.io/wireup/latest/testing/).
- **Reusable sub-graphs**: run multiple configured instances of the same dependency graph without spinning up separate containers. [See reusable factory bundles](https://maldoinc.github.io/wireup/latest/factories/#reusable-factory-bundles).

## Installation

```bash
pip install wireup
```


## Complete Example

```python
@injectable
class Database:
    def query(self, sql: str) -> list[str]: ...

@injectable
class UserService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_users(self) -> list[str]:
        return self.db.query("SELECT name FROM users")

app = fastapi.FastAPI()

@app.get("/users")
def get_users(service: Injected[UserService]) -> list[str]:
    return service.get_users()

container = wireup.create_async_container(injectables=[Database, UserService])
wireup.integration.fastapi.setup(container, app)
```

For a fully working end-to-end walkthrough, see the [Getting Started guide](https://maldoinc.github.io/wireup/latest/getting_started/).

## Features

### ⚡ Clean & Type-Safe DI

Use decorators and annotations for concise, co-located definitions, or factories to keep your domain model pure and decoupled.

**1. Basic Usage**

Register classes with `@injectable` and let the container resolve dependencies automatically.

```python
@injectable
class Database:
    def __init__(self) -> None:
        self.engine = sqlalchemy.create_engine("sqlite://")

@injectable
class UserService:
    def __init__(self, db: Database) -> None:
        self.db = db

container = wireup.create_sync_container(injectables=[Database, UserService])

# Inject via framework integration or @inject_from_container (recommended)
@app.get("/users")
def get_users(service: Injected[UserService]) -> list[str]: ...

# Or resolve directly for advanced use cases (middleware, startup, scripts)
user_service = container.get(UserService)
```

**2. Inject Configuration**

Inject configuration alongside dependencies. No need to write factories just to pass a config value.

<details>
<summary>View Code</summary>

```python
@injectable
class Database:
    def __init__(self, url: Annotated[str, Inject(config="db_url")]) -> None:
        self.engine = sqlalchemy.create_engine(url)

container = wireup.create_sync_container(
    injectables=[Database],
    config={"db_url": os.environ["DB_URL"]}
)
```

</details>

**3. Clean Architecture**

Need strict boundaries? Use factories to wire pure domain objects and integrate external libraries like Pydantic.

```python
# 1. No Wireup imports
class Database:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(url)

# 2. Configuration (Pydantic)
class Settings(BaseModel):
    db_url: str = "sqlite://"
```

```python
# 3. Wireup factories
@injectable
def make_settings() -> Settings:
    return Settings()

@injectable
def make_database(settings: Settings) -> Database:
    return Database(url=settings.db_url)

container = wireup.create_sync_container(injectables=[make_settings, make_database])
```

**4. Auto-Discover**

No need to list every injectable manually. Scan entire modules or packages to register all at once. This is the recommended default for larger applications.

<details>
<summary>View Code</summary>

```python
import app
import wireup

container = wireup.create_sync_container(
    injectables=[
        app.services,
        app.repositories,
        app.factories
    ]
)
```

</details>

### 🎯 Function Injection

Inject dependencies into any function. CLI commands, background tasks, event handlers, or any standalone function that needs container access.

```python
@inject_from_container(container)
def migrate_database(db: Injected[Database], settings: Injected[Settings]) -> None:
    ...
```

### 📝 Interfaces & Abstractions

Depend on abstractions, not implementations. Bind implementations to interfaces using Protocols or ABCs.

```python
class Notifier(Protocol):
    def notify(self) -> None: ...

@injectable(as_type=Notifier)
class SlackNotifier:
    def notify(self) -> None: ...

container = create_sync_container(injectables=[SlackNotifier])

# SlackNotifier is injected wherever Notifier is requested
@app.post("/notify")
def send_notification(notifier: Injected[Notifier]) -> None:
    notifier.notify()
```

### 🏭 Flexible Creation Patterns

Defer instantiation to factories when initialization or cleanup is non-trivial. Full support for sync, async, and generator factories. Wireup handles cleanup at the right time based on lifetime.

```python
class WeatherClient:
    def __init__(self, client: requests.Session) -> None:
        self.client = client

@injectable
def weather_client_factory() -> Iterator[WeatherClient]:
    with requests.Session() as session:
        yield WeatherClient(client=session)
```

<details>
<summary>Async example</summary>

```python
class WeatherClient:
    def __init__(self, client: aiohttp.ClientSession) -> None:
        self.client = client

@injectable
async def weather_client_factory() -> AsyncIterator[WeatherClient]:
    async with aiohttp.ClientSession() as session:
        yield WeatherClient(client=session)
```

</details>


### 🔄 Managed Lifetimes

Declare dependencies as singleton, scoped, or transient to control instance reuse.

```python
# Singleton: one instance per application (default)
@injectable
class Settings:
    pass

# Async singleton with cleanup — no lru_cache, no app.state
@injectable
async def database_factory(settings: Settings) -> AsyncIterator[AsyncConnection]:
    async with create_async_engine(settings.db_url).connect() as connection:
        yield connection

# Scoped: one instance per request, shared within that request
@injectable(lifetime="scoped")
class RequestContext:
    def __init__(self) -> None:
        self.request_id = uuid4()

# Transient: fresh instance every time
@injectable(lifetime="transient")
class OrderProcessor:
    pass
```


### ❓ Optional Dependencies

First-class support for `Optional[T]` and `T | None`.

```python
@injectable
def make_cache(settings: Settings) -> RedisCache | None:
    return RedisCache(settings.redis_url) if settings.cache_enabled else None

@injectable
class UserService:
    def __init__(self, cache: RedisCache | None) -> None:
        self.cache = cache

# Retrieve optional dependencies directly when needed
cache = container.get(RedisCache | None)
```

### 🧩 Reusable sub-graphs

Need to register multiple sub-graphs with different settings (e.g. primary + analytics DB)?

Wireup supports this natively without requiring a dedicated provider class or a separate container. 
See [Reusable Factory Bundles](https://maldoinc.github.io/wireup/latest/factories/#reusable-factory-bundles).


### 🛡️ Startup Validation

Wireup validates the entire dependency graph when the container is created.

```python
# Missing dependencies: caught at startup, not at runtime
@injectable
class Foo:
    def __init__(self, unknown: NotManagedByWireup) -> None: ...

container = wireup.create_sync_container(injectables=[Foo])
# ❌ Parameter 'unknown' of 'Foo' depends on an unknown injectable 'NotManagedByWireup'.
```

```python
container = wireup.create_sync_container(injectables=[])

# Decorated functions validated at import time
@inject_from_container(container)
def my_function(oops: Injected[NotManagedByWireup]): ...
# ❌ Parameter 'oops' of 'my_function' depends on an unknown injectable 'NotManagedByWireup'.

```

```python
# Missing config keys caught at startup
@injectable
class Database:
    def __init__(self, url: Annotated[str, Inject(config="db_url")]) -> None: ...

container = wireup.create_sync_container(injectables=[Database], config={})
# ❌ Parameter 'url' of Type 'Database' depends on an unknown Wireup config key 'db_url'.
```

Additional checks: circular dependencies, lifetime mismatches (e.g. singleton depending on scoped), and duplicate registrations.

### 📍 Framework Independent

Define your service layer once. Run it anywhere.

```python
# Define once
# injectables = [UserService, Database, ...]

# FastAPI (native integration, no extra decorator needed)
@app.get("/users")
async def view(service: Injected[UserService]): ...

# Click
@click.command()
def command(service: Injected[UserService]): ...

# Use @inject_from_container to inject dependencies into any function.
# Most useful for scripts or when no Wireup integration is available.
@inject_from_container(container)
def run_worker(service: Injected[UserService]): ...
```

Have a useful integration to recommend? Create an issue or PR!


### 🔌 Framework Integrations

Native integrations manage request scopes, endpoint injection, and dependency lifetimes.

Supported: **FastAPI**, **Flask**, **Django**, **AIOHTTP**, **Starlette**, **Click**, **Typer**, **Strawberry**

[View all integrations →](https://maldoinc.github.io/wireup/latest/integrations/)

### 🧪 Simplified Testing

Wireup decorators only collect metadata. Injectables are plain classes and functions. Test them directly with no special setup.

Swap dependencies during tests with `container.override`:

```python
with container.override.injectable(target=Database, new=in_memory_database):
    # All code that depends on Database will receive in_memory_database
    # for the duration of this context manager
    response = client.get("/users")
```

## 📚 Documentation

[https://maldoinc.github.io/wireup](https://maldoinc.github.io/wireup)

If Wireup helps your team move faster, consider starring the repo to help more Python developers discover it.
