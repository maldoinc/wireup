<div align="center">
<h1>Wireup</h1>
<p>
Type-driven dependency injection for Python. Wireup is battle-tested in production, thread-safe, no-GIL (PEP 703) ready, and fail-fast by design: <strong>if the container starts, it works</strong>.
</p>

[![GitHub](https://img.shields.io/github/license/maldoinc/wireup)](https://github.com/maldoinc/wireup)
[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/maldoinc/wireup/run_all.yml)](https://github.com/maldoinc/wireup)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup)](https://pypi.org/project/wireup/)
[![PyPI - Version](https://img.shields.io/pypi/v/wireup)](https://pypi.org/project/wireup/)
<br />

</div>

<p align="center">
  <a href="#quick-start"><strong>Quick Start</strong></a> &middot;
  <a href="https://maldoinc.github.io/wireup"><strong>Docs</strong></a> &middot;
  <a href="https://maldoinc.github.io/wireup/latest/benchmarks/"><strong>Benchmarks</strong></a> &middot;
  <a href="https://maldoinc.github.io/wireup/latest/migrate_to_wireup/"><strong>Migrate to Wireup</strong></a>
</p>

## Why Wireup?

<table>
<tr>
<td align="center" valign="top" width="33%">
<h3>🔁 Define Once, Use Anywhere</h3>
Reuse the same application code in APIs, CLIs, workers, and scripts without rewriting your wiring.
</td>
<td align="center" valign="top" width="33%">
<h3>✅ Correct by Default</h3>
If the container starts, your dependency graph is valid. Wireup checks for missing or misconfigured dependencies to avoid surprises at runtime. See <a href="https://maldoinc.github.io/wireup/latest/what_wireup_validates/">What Wireup Validates</a>
</td>
<td align="center" valign="top" width="33%">
<h3>🌐 Framework-Ready</h3>
Native integrations for <strong>FastAPI</strong>, <strong>Django</strong>, <strong>Flask</strong>, <strong>Starlette</strong>, <strong>Celery</strong>, <strong>Click</strong>, <strong>Typer</strong>, and more.
</td>
</tr>
<tr>
<td align="center" valign="top">
<h3>⚡ Zero-Overhead Handlers</h3>
Resolve singleton constructor dependencies once at startup in <a href="https://maldoinc.github.io/wireup/latest/integrations/fastapi/class_based_handlers/">FastAPI</a> and <a href="https://maldoinc.github.io/wireup/latest/integrations/aiohttp/class_based_handlers/">AIOHTTP</a> class-based handlers, not per request.
</td>
<td align="center" valign="top">
<h3>🧩 Advanced Wiring</h3>
Go beyond simple constructor injection with
<a href="https://maldoinc.github.io/wireup/latest/reusable_bundles/">reusable bundles</a>,
<a href="https://maldoinc.github.io/wireup/latest/lifetimes_and_scopes/">explicit scope context sharing</a>, and
more using plain Python.
</td>
<td align="center" valign="top">
<h3>🧪 Easy to test</h3>
Override dependencies with context managers, keep tests isolated, and restore the original graph automatically.
</td>
</tr>
</table>

## Benchmarks

<p align="center">
    <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/pages/img/benchmarks_scoped_dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/pages/img/benchmarks_scoped_light.svg">
    <img alt="Scoped Dependency Injection Performance" src="docs/pages/img/benchmarks_scoped_light.svg" height="300">
    </picture>
</p>

<p align="center">
    <i>Dense dependency graph resolved per request in FastAPI + Uvicorn<br>
    (Requests per second, higher is better. Manual Wiring represents the upper bound.)<br>
    Full methodology and reproducibility: <a href="https://maldoinc.github.io/wireup/latest/benchmarks/">benchmarks</a>.</i>
</p>

## Installation

```bash
pip install wireup
```


## Quick Start

```python
import fastapi
import wireup
import wireup.integration.fastapi
from wireup import Injected, injectable


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

For a full end-to-end walkthrough, start with the [Getting Started guide](https://maldoinc.github.io/wireup/latest/getting_started/).

## Basic Usage

Wireup also supports config injection, decorator-free domain models, and package-level registration.

**1. Inject Configuration**

Inject configuration alongside dependencies. No need to write factories just to pass a config value.

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

**2. Clean Architecture**

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

**3. Package-level registration**

No need to list every injectable manually. Provide entire modules or packages to register all at once.

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

## More Features

### 🎯 Function Injection

Inject dependencies into CLI commands, background tasks, event handlers, or any standalone function that needs container access.

```python
@inject_from_container(container)
def migrate_database(db: Injected[Database], settings: Injected[Settings]) -> None:
    ...
```

### 📝 Interfaces & Abstractions

Bind implementations to interfaces using Protocols or ABCs.

```python
class Notifier(Protocol):
    def notify(self) -> None: ...

@injectable(as_type=Notifier)
class SlackNotifier:
    def notify(self) -> None: ...

# SlackNotifier is injected wherever Notifier is requested
@app.post("/notify")
def send_notification(notifier: Injected[Notifier]) -> None:
    notifier.notify()
```

### 🏭 Factories & Resources

Defer instantiation to specialized factories when complex initialization or cleanup is required. 
Full support for sync, async, and generator factories. Wireup handles cleanup at the right time based on lifetime.

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


### 🔄 Lifetimes & Scopes

Declare dependencies as `singleton`, `scoped`, or `transient` to control reuse explicitly.

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

### 🛡️ Startup Validation

Wireup validates the dependency graph when the container is created. See <a href="https://maldoinc.github.io/wireup/latest/what_wireup_validates/">What Wireup Validates</a> for the full rules and limits.

```python
# Missing dependencies: caught at startup, not at runtime
@injectable
class Foo:
    def __init__(self, unknown: NotManagedByWireup) -> None: ...

container = wireup.create_sync_container(injectables=[Foo])
# ❌ Parameter 'unknown' of 'Foo' depends on an unknown injectable 'NotManagedByWireup'.
```

It also catches circular dependencies, duplicate registrations, misconfigured lifetimes, and missing config at startup.

### 🧪 Testing

Wireup decorators only collect metadata. Injectables are plain classes and functions, so you can test them directly with no special setup.

Swap dependencies during tests with `container.override`:

```python
with container.override.injectable(target=Database, new=in_memory_database):
    # Injectables that depend on Database will receive in_memory_database
    # for the duration of this context manager
    response = client.get("/users")
```

## 📚 Documentation

See the docs for integrations, lifetimes, factories, testing, and more advanced patterns.

[https://maldoinc.github.io/wireup](https://maldoinc.github.io/wireup)

If Wireup is useful to you, a star on GitHub helps others find it.
