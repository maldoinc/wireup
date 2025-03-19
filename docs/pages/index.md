Performant, concise, and easy-to-use Dependency Injection container for Python 3.8+.

[![GitHub](https://img.shields.io/github/license/maldoinc/wireup)](https://github.com/maldoinc/wireup)
[![Coverage](https://img.shields.io/codeclimate/coverage/maldoinc/wireup?label=Coverage)](https://codeclimate.com/github/maldoinc/wireup)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup)](https://pypi.org/project/wireup/)
[![PyPI - Version](https://img.shields.io/pypi/v/wireup)](https://pypi.org/project/wireup/)

!!! note "What is Dependency Injection?"
    Dependency Injection is a design pattern where objects receive their dependencies externally instead of creating them.
    Wireup manages the creation, injection, and lifecycle of dependencies. It uses typing to automatically
    resolve dependencies, reducing boilerplate and supports modern Python features like async and generators.

## Why Wireup?

### 🎯 Dependency Injection made (extremely) simple

Inject services and configuration using a clean and intuitive syntax without boilerplate.

=== "Basic Example"

    ```python
    @service
    class Database:
        pass

    @service
    class UserService:
        def __init__(self, db: Database) -> None:
            self.db = db

    container = wireup.create_sync_container(services=[Database, UserService])
    user_repository = container.get(UserService)
    # ✅ Dependencies resolved.
    ```

=== "With Configuration"

    ```python
    @service
    class Database:
        def __init__(self, db_url: Annotated[str, Inject(param="db_url")]) -> None:
            self.db_url = db_url

    @service
    class UserService:
        def __init__(self, db: Database) -> None:
            self.db = db

    container = wireup.create_sync_container(
        services=[Database, UserService], 
        parameters={"db_url": os.environ.get("APP_DB_URL")}
    )
    user_repository = container.get(UserService)
    db_url = container.params.get("db_url")
    # ✅ Dependencies resolved.
    ```


### @ Apply as a Decorator

Apply the container as a decorator to inject the required dependencies directly into any function.

```python
from wireup import Injected, inject_from_container

@inject_from_container(container)
def my_awesome_function(repo: Injected[UserService]):
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

=== "Singleton"

    One instance per application. `@service(lifetime="singleton")` is the default.

    ```python
    @service
    class Database:
        pass
    ```

=== "Scoped"

    One instance per scope/request, shared within that scope/request.

    ```python
    @service(lifetime="scoped")
    class RequestContext:
        def __init__(self) -> None:
            self.request_id = uuid4()
    ```

=== "Transient"

    When full isolation and clean state is required. Every request to create transient services results in a new instance.

    ```python
    @service(lifetime="transient")
    class OrderProcessor:
        pass
    ```

### 🏭 Flexible Creation Patterns

Defer instantiation to specialized factories when complex initialization or cleanup is required.
Full support for async and generators. Wireup will take care of cleanup at the correct time depending on the service
lifetime.

=== "Synchronous"

    ```python
    class WeatherClient:
        def __init__(self, client: requests.Session) -> None:
            self.client = client

    @service
    def weather_client_factory() -> Iterator[Weatherclient]:
        with requests.Session() as sess:
            yield WeatherClient(client=sess)
    ```

=== "Async"

    ```python
    class WeatherClient:
        def __init__(self, client: aiohttp.ClientSession) -> None:
            self.client = client

    @service
    async def weather_client_factory() -> AsyncIterator[Weatherclient]:
        async with aiohttp.ClientSession() as sess:
            yield WeatherClient(client=sess)
    ```


### 🛡️ Improved Safety

Wireup is mypy strict compliant and will not introduce type errors in your code.

It will also warn you at the earliest possible stage about configuration errors to avoid surprises.


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

    Injected functions will raise at module import time rather than on when called.

    ```python
    @inject_from_container(container)
    def my_function(oops: Injected[NotManagedByWireup]):
        pass

    # ❌ Parameter 'oops' of 'my_function' depends on an unknown service 'NotManagedByWireup'.
    ```

=== "Integrations"

    Wireup integrations assert that requested injections in the framework are valid.
    ```python
    @app.get("/")
    def home(foo: Injected[NotManagedByWireup]):
        pass


    wireup.integration.flask.setup(container, app)
    # ❌ Parameter 'oops' of 'home' depends on an unknown service 'NotManagedByWireup'.
    ```


=== "Parameter Checks"

    Configuration parameters are also checked for validity.
    ```python
    class Database:
        def __init__(self, url: Annotated[str, Inject(param="db_url")]) -> None:
            self.db = db

    # ❌ Parameter 'url' of Type 'Database' depends on an unknown Wireup parameter 'db_url'.
    ```

### 📍 Framework-agnostic

Wireup provides its own Dependency Injection mechanism and is not tied things like http. You can use it anywhere
you like.

### 🫶 Share services between application and cli

If your Web application has an accompanying CLI, you can use Wireup to share the service layer between.

### 🔌 Native Integration with Django, FastAPI or Flask

Integrate with popular frameworks for a smoother developer experience.
Integrations will manage request scopes, injection in endpoints and lifecycle of servies.

```python
app = FastAPI()
container = wireup.create_async_container(services=[UserService, Database])

@app.get("/")
def users_list(user_service: Injected[UserService]):
    pass

wireup.integration.fastapi.setup(container, app)
```

## Next Steps

* [Quickstart](getting_started.md) - Follow the quickstart guide for a more in-depth tutorial.
* [Services](services.md)
* [Parameters](parameters.md)