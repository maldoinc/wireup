Wireup is a performant, concise, and easy-to-use Dependency Injection container for Python 3.8+.

[![GitHub](https://img.shields.io/github/license/maldoinc/wireup)](https://github.com/maldoinc/wireup)
[![Coverage](https://img.shields.io/codeclimate/coverage/maldoinc/wireup?label=Coverage)](https://codeclimate.com/github/maldoinc/wireup)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup)](https://pypi.org/project/wireup/)
[![PyPI - Version](https://img.shields.io/pypi/v/wireup)](https://pypi.org/project/wireup/)

??? note "What is Dependency Injection?"
    Dependency Injection (DI) is a design pattern where objects receive their dependencies externally instead of creating them.
    Wireup manages the creation, injection, and lifecycle of dependencies. It uses typing to automatically
    resolve dependencies, reducing boilerplate and supporting modern Python features like async and generators.

## Why Wireup?

### 💉 Dependency Injection Made Simple

Inject services and configuration using a clean and intuitive syntax.

```python
@service
class Database:
    def __init__(self, db_url: Annotated[str, Inject(param="db_url")]) -> None:
        self.db_url = db_url

@service
class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

container = wireup.create_sync_container(
    services=[Database, UserRepository], 
    parameters={"db_url": "postgresql://"}
)
user_repository = container.get(UserRepository) # Dependencies resolved.
```

### 🎯 Apply as a Decorator

Don't want to do `container.get` calls? Wireup lets you apply the container as a decorator.

```python
from wireup import Injected, inject_from_container

@inject_from_container(container)
def my_awesome_function(repo: Injected[UserRepository]):
    pass
```

### 🔌 Native Integration with Django, FastAPI, Flask

Integrate seamlessly with your favorite web frameworks in just two lines of code!

```python
app = FastAPI()
container = wireup.create_async_container()

wireup.integration.fastapi.setup(container, app)
```

### 📝 Interfaces & Abstract Classes

Define abstract types and have the container automatically inject the implementation.

```python
@abstract
class Notifier:
    pass


@service
class SlackNotifier(Notifier):
    pass


notifier = container.get(Notifier)  # SlackNotifier instance.
```

### 🏭 Flexible Creation Patterns

Defer instantiation to specialized factories for full control over object creation when necessary.
Full support for async and generators. Wireup will take care of cleanup.

=== "Synchronous"

    ```python
    class WeatherClient:
        def __init__(self, client: requests.Session) -> None:
            self.client = client

    @service
    def http_client_factory() -> Iterator[Weatherclient]:
        async with requests.Session() as sess:
            yield WeatherClient(client=sess)
    ```

=== "Async"

    ```python
    class WeatherClient:
        def __init__(self, client: aiohttp.ClientSession) -> None:
            self.client = client

    @service
    async def http_client_factory() -> AsyncIterator[Weatherclient]:
        async with aiohttp.ClientSession() as sess:
            yield WeatherClient(client=sess)
    ```

### 🔄 Managed Service Lifetimes

Declare dependencies as singletons, scoped, or transient to control whether to inject a fresh copy or reuse existing instances.

### 🛡️ Safe

Wireup will warn you at the earliest possible stage about misconfigurations to avoid runtime surprises.

```python title="Container Creation"
class NotManagedByWireup:
    pass


@service
class Foo:
    def __init__(self, unknown: NotManagedByWireup) -> None:
        pass


container = wireup.create_sync_container(services=[Foo])
# ❌ Parameter 'unknown' of 'Foo' depends on an unknown service 'NotManagedByWireup'.
```

Injected functions will raise at module import time rather than on call.

```python title="Function injection"
@inject_from_container(container)
def my_function(oops: Injected[NotManagedByWireup]):
    pass

# ❌ Parameter 'oops' of 'my_function' depends on an unknown service 'NotManagedByWireup'.
```
