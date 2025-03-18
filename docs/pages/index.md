Wireup is a performant, concise, and easy-to-use Dependency Injection container for Python 3.8+.

[![GitHub](https://img.shields.io/github/license/maldoinc/wireup)](https://github.com/maldoinc/wireup)
[![Coverage](https://img.shields.io/codeclimate/coverage/maldoinc/wireup?label=Coverage)](https://codeclimate.com/github/maldoinc/wireup)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup)](https://pypi.org/project/wireup/)
[![PyPI - Version](https://img.shields.io/pypi/v/wireup)](https://pypi.org/project/wireup/)

!!! note "What is Dependency Injection?"
    Dependency Injection is a design pattern where objects receive their dependencies externally instead of creating them.
    Wireup manages the creation, injection, and lifecycle of dependencies. It uses typing to automatically
    resolve dependencies, reducing boilerplate and supporting modern Python features like async and generators.

## Why Wireup?

### 🎯 Dependency Injection Made Simple

Inject services and configuration using a clean and intuitive syntax.

=== "Basic Example"

    ```python
    @service
    class Database:
        def __init__(self) -> None:
            self.db_url = "postgresql://"

    @service
    class UserRepository:
        def __init__(self, db: Database) -> None:
            self.db = db

    container = wireup.create_sync_container(
        services=[Database, UserRepository], 
    )
    user_repository = container.get(UserRepository)
    # ✅ Dependencies resolved.
    ```

=== "With Configuration"

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
        parameters={"db_url": os.environ.get("APP_DB_URL")}
    )
    user_repository = container.get(UserRepository)
    db_url = container.params.get("db_url")
    # ✅ Dependencies resolved.
    ```


### @ Apply as a Decorator

Don't want to do `container.get` calls? Wireup lets you apply the container as a decorator.

```python
from wireup import Injected, inject_from_container

@inject_from_container(container)
def my_awesome_function(repo: Injected[UserRepository]):
    # ✅ UserRepository injected.
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
class Notifier(abc.ABC):
    pass


@service
class SlackNotifier(Notifier):
    pass


notifier = container.get(Notifier)
# ✅ SlackNotifier instance.
```

### 🏭 Flexible Creation Patterns

Defer instantiation to specialized factories when complex initialization or cleanup is required.
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


=== "Container Creation"

    Container will raise at creation time about missing dependencies or other errors.

    ```python
    @service
    class Foo:
        def __init__(self, unknown: NotManagedByWireup) -> None:
            pass


    container = wireup.create_sync_container(services=[Foo])
    # ❌ Parameter 'unknown' of 'Foo' depends on an unknown service 'NotManagedByWireup'.
    ```

=== "Function injection"

    Injected functions will raise at module import time rather than on call.

    ```python
    @inject_from_container(container)
    def my_function(oops: Injected[NotManagedByWireup]):
        pass

    # ❌ Parameter 'oops' of 'my_function' depends on an unknown service 'NotManagedByWireup'.
    ```

=== "Integrations"

    When using the Wireup integrations all dependencies are checked for validity.
    ```python
    @app.get("/")
    def home(foo: Injected[NotManagedByWireup]):
        pass


    wireup.integration.flask.setup(container, app)
    # ❌ Parameter 'oops' of 'home' depends on an unknown service 'NotManagedByWireup'.
    ```

## Next Steps

* [Quickstart](getting_started.md) - Follow the quickstart guide for a more in-depth tutorial.
* [Services](services.md)
* [Parameters](parameters.md)