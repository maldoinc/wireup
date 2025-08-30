<div align="center">
<h1>Wireup</h1>
<p>Performant, concise and type-safe Dependency Injection for Python 3.8+</p>

[![GitHub](https://img.shields.io/github/license/maldoinc/wireup)](https://github.com/maldoinc/wireup)
[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/maldoinc/wireup/run_all.yml)](https://github.com/maldoinc/wireup)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup)](https://pypi.org/project/wireup/)
[![PyPI - Version](https://img.shields.io/pypi/v/wireup)](https://pypi.org/project/wireup/)
[![Documentation](https://img.shields.io/badge/%F0%9F%93%9A%20Documentation-3D9970)](https://maldoinc.github.io/wireup)
</div>

Dependency Injection (DI) is a design pattern where dependencies are provided externally rather than created within objects. Wireup automates dependency management using Python's type system, with support for async, generators, modern Python features and integrations for FastAPI, Django, Flask and AIOHTTP out of the box.

> [!TIP]
> **New**: Inject Dependencies in FastAPI with zero runtime overhead using [Class-Based Handlers](https://maldoinc.github.io/wireup/latest/integrations/fastapi/class_based_handlers/).


## Features

### ✨ Simple & Type-Safe DI

Inject services and configuration using a clean and intuitive syntax.

```python
@service
class Database:
    pass

@service
class UserService:
    def __init__(self, db: Database) -> None:
        self.db = db

container = wireup.create_sync_container(services=[Database, UserService])
user_service = container.get(UserService) # ✅ Dependencies resolved.
```

<details>
<summary>Example With Configuration</summary>

```python
@service
class Database:
    def __init__(self, db_url: Annotated[str, Inject(param="db_url")]) -> None:
        self.db_url = db_url

container = wireup.create_sync_container(
    services=[Database], 
    parameters={"db_url": os.environ["APP_DB_URL"]}
)
database = container.get(Database) # ✅ Dependencies resolved.
```

</details>

### 🎯 Function Injection

Inject dependencies directly into functions with a simple decorator.

```python
@inject_from_container(container)
def process_users(service: Injected[UserService]):
    # ✅ UserService injected.
    pass
```

### 📝 Interfaces & Abstract Classes

Define abstract types and have the container automatically inject the implementation.

```python
@abstract
class Notifier(abc.ABC):
    pass

@service
class SlackNotifier(Notifier):
    pass

notifier = container.get(Notifier)
# ✅ SlackNotifier instance.
```


### 🔄 Managed Service Lifetimes

Declare dependencies as singletons, scoped, or transient to control whether to inject a fresh copy or reuse existing instances.


```python
# Singleton: One instance per application. `@service(lifetime="singleton")` is the default.
@service
class Database:
    pass

# Scoped: One instance per scope/request, shared within that scope/request.
@service(lifetime="scoped")
class RequestContext:
    def __init__(self) -> None:
        self.request_id = uuid4()

# Transient: When full isolation and clean state is required.
# Every request to create transient services results in a new instance.
@service(lifetime="transient")
class OrderProcessor:
    pass
```


### 🏭 Flexible Creation Patterns

Defer instantiation to specialized factories when complex initialization or cleanup is required.
Full support for async and generators. Wireup handles cleanup at the correct time depending on the service lifetime.

**Synchronous**

```python
class WeatherClient:
    def __init__(self, client: requests.Session) -> None:
        self.client = client

@service
def weather_client_factory() -> Iterator[WeatherClient]:
    with requests.Session() as session:
        yield WeatherClient(client=session)
```

**Async**

```python
class WeatherClient:
    def __init__(self, client: aiohttp.ClientSession) -> None:
        self.client = client

@service
async def weather_client_factory() -> AsyncIterator[WeatherClient]:
    async with aiohttp.ClientSession() as session:
        yield WeatherClient(client=session)
```


### 🛡️ Improved Safety

Wireup is mypy strict compliant and will not introduce type errors in your code. It will also warn you at the earliest possible stage about configuration errors to avoid surprises.

**Container Creation**

The container will raise errors at creation time about missing dependencies or other issues.

```python
@service
class Foo:
    def __init__(self, unknown: NotManagedByWireup) -> None:
        pass

container = wireup.create_sync_container(services=[Foo])
# ❌ Parameter 'unknown' of 'Foo' depends on an unknown service 'NotManagedByWireup'.
```

**Function Injection**

Injected functions will raise errors at module import time rather than when called.

```python
@inject_from_container(container)
def my_function(oops: Injected[NotManagedByWireup]):
    pass

# ❌ Parameter 'oops' of 'my_function' depends on an unknown service 'NotManagedByWireup'.
```

**Integrations**

Wireup integrations assert that requested injections in the framework are valid.

```python
@app.get("/")
def home(foo: Injected[NotManagedByWireup]):
    pass

wireup.integration.flask.setup(container, app)
# ❌ Parameter 'foo' of 'home' depends on an unknown service 'NotManagedByWireup'.
```

### 📍 Framework-Agnostic

Wireup provides its own Dependency Injection mechanism and is not tied to specific frameworks. Use it anywhere you like.

### 🔗 Share Services Between Application and CLI

Share the service layer between your web application and its accompanying CLI using Wireup.

### 🔌 Native Integration with Django, FastAPI, Flask, AIOHTTP, Click and Starlette

Integrate with popular frameworks for a smoother developer experience.
Integrations manage request scopes, injection in endpoints, and lifecycle of services.

```python
app = FastAPI()
container = wireup.create_async_container(services=[UserService, Database])

@app.get("/")
def users_list(user_service: Injected[UserService]):
    pass

wireup.integration.fastapi.setup(container, app)
```

### 🧪 Simplified Testing

Wireup does not patch your services and lets you test them in isolation.

If you need to use the container in your tests, you can have it create parts of your services
or perform dependency substitution.

```python
with container.override.service(target=Database, new=in_memory_database):
    # The /users endpoint depends on Database.
    # During the lifetime of this context manager, requests to inject `Database`
    # will result in `in_memory_database` being injected instead.
    response = client.get("/users")
```

## 📚 Documentation

For more information [check out the documentation](https://maldoinc.github.io/wireup)
