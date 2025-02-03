Wireup is a Performant, concise, and easy-to-use Dependency Injection container for Python 3.8+.

Dependency Injection (DI) is a design pattern where objects receive their dependencies externally instead of creating them.
Wireup manages the creation, injection, and lifecycle management of dependencies. It uses typing to automatically
resolve dependencies where required, reducing boilerplate and supports modern Python features such as async and generators.

It can function standalone as a DI container or service locator and also integrates with popular frameworks such as Django, FastAPI and Flask.

## Quickstart

To showcase the basics of Wireup, we will create a container able to inject the following:

* A `WeatherService` that queries a fictional weather api, needs an api key and, a `KeyValueStore` to cache request data and an async http client
* `KeyValueStore` itself needs a `redis_url` denoting the server it will connect to to query/store data.

These services will then be retrieved in a `/weather/forecast` endpoint that requires `WeatherService` to provide weather information.

``` mermaid
graph LR
    A --> C
    B --> D
    C --> D
    D --> E
    F --> D

    A[⚙️ redis_url]
    B[⚙️ weather_api_key]
    C[🐍 KeyValueStore]
    D[🐍 WeatherService]
    E[🌎 /weather/forecast]
    F[🏭 HttpClient]
```

### 1. Setup

Install wireup using pip or your favorite package manager.

```shell
$ pip install wireup
```

The first step is to create a container.

```python title="container.py"
import wireup

container = wireup.create_container(
    # Parameters serve as application/service configuration.
    parameters={
        "redis_url": os.environ["APP_REDIS_URL"],
        "weather_api_key": os.environ["APP_WEATHER_API_KEY"],
    },
    # Let the container know where service registrations are located.
    service_modules=[services]
)
```

Parameters are configuration your application needs. Such as an api key, database url, or other settings.
Service modules is a list of top-level python modules containing service definitions this container needs to know about.


??? abstract "Read: Global variables"
    Using this approach means relying on global state, which ties your application to a single container instance. 
    This might be sufficient for you and that's okay but, if you want to avoid global state, it's better to create 
    the container within your application factory and provide a way to access it from the created application instance.

    With the available integrations, global state is neither necessary nor recommended.


### 2. Define services

The container uses configuration metadata from annotations and types to define services and the dependencies between them.
This means that the service declaration is self-contained and does not require additional setup for most use cases.


#### 🐍 `KeyValueStore`
To create `KeyValueStore`, all we need is the `redis_url` parameter.
The `@service` decorator tells Wireup this is a service, and we simply need to tell the container via annotated types
to fetch the value of the `redis_url` parameter for `dsn`. 


```python title="services/key_value_store.py" hl_lines="4 6"
from wireup import service, Inject
from typing_extensions import Annotated

@service  #(1)!
class KeyValueStore:
    def __init__(self, dsn: Annotated[str, Inject(param="redis_url")]) -> None:  #(2)!
        self.client = redis.from_url(dsn)
```


1. Decorators are used to collect metadata. 
    This makes testing simpler, as you can still instantiate this like a regular class in your tests.
2. Parameters must be annotated with the `Inject(param=name)` syntax. This tells the container which parameter to inject.


#### 🐍 `WeatherService`
Creating `WeatherService` is also straightforward. The `@service` decorator is used to let Wireup know this is a service
and we use the same syntax as above for the `api_key`. Class dependencies do not need additional annotations in this case.

```python title="services/weather_service.py" hl_lines="1 5 6 7"
@service
class WeatherService:
    def __init(
        self,
        api_key: Annotated[str, Inject(param="weather_api_key")], #(1)!
        kv_store: KeyValueStore, #(2)!
        client: aiohttp.ClientSession, #(2)!
    ) -> None:
        self.api_key = api_key
        self.kv_store = kv_store
```

1. Same as above, weather api key needs the parameter name for the container to inject it.
2. `KeyValueStore` and `aiohttp.ClientSession` can be injected only by type and requires no additional configuration.

#### 🏭 `aiohttp.ClientSession`

The http client making requests cannot be instantiated directly as we need to enter an async context manager.
To accomodate such cases, Wireup allows you to use functions to create dependencies. 
These can be sync/async as well as regular or generator functions if cleanup needs to take place.

Factories can define their dependencies in the function's signature.

**Note:** When using generator factories make sure to call `container.close` (or `container.aclose()` for async generators)
when the application is terminating for the necessary cleanup to take place.

```python title="services/factories.py"
@service
async def make_http_client() -> AsyncIterator[aiohttp.ClientSession]:
    async with aiohttp.ClientSession() as client:
        yield client
```

!!! tip "Use Wireup without annotations"
    If using annotations is not suitable for your project, you can use factories as shown above to create
    all dependencies.

    This lets you keep service definitions devoid of Wireup references. [Learn more](factory_functions.md)

### 3. Use

Use the container as a service locator or apply it as a decorator.

=== "Injection via decorator"

    The container instance provides an `autowire` method that when applied
    to a function will cause the container to pass the dependencies
    when the function is called.

    ```python title="views/posts.py"  hl_lines="2 3"
    @app.get("/weather/forecast")
    @container.autowire
    async def get_forecast_view(weather_service: WeatherService):
        return await weather_service.get_forecast(...)
    ```

=== "Service Locator"

    Alternatively you can use the container's ability to function as a service locator.
    Simply call `.get` on the container instance with the type you wish to retrieve.

    ```python title="views/posts.py"  hl_lines="3"
    @app.get("/weather/forecast")
    async def get_forecast_view():
        weather_service = container.get(WeatherService)
        return await weather_service.get_forecast(...)
    ```



#### 3.5 Integrate

While Wireup is framework-agnostic, usage can be simplified when using it alongside one of the integrations.
A key benefit of the integrations, is removing the need to have a global container variable
and the need to decorate injection targets in the frameworks.

Each integration also comes with additional goodies specific to that framework.

- [Django](integrations/django.md)
- [FastAPI](integrations/fastapi.md)
- [Flask](integrations/flask.md)

### 4. Test

Wireup does not patch your services, which means they can be instantiated and tested independently of the container.

To substitute dependencies on autowired targets such as views in a web application you can override dependencies with new ones on the fly.


```python
with container.override.service(WeatherService, new=test_weather_service):
    response = client.get("/weather/forecast")
```

Requests to inject `WeatherService` during the lifetime of the context manager 
will result in `test_weather_service` being injected instead.

## Conclusion

This concludes the "Getting Started" walkthrough, covering the most common dependency injection use cases.

!!! info
    * The `@container.autowire` decorator is not needed for services.
    * When using the provided integrations,
    decorating views with `@container.autowire` is no longer required.
    * Wireup can perform injection on both sync and async targets.
    * Every container you create is separate from the rest and has its own state.

## Next Steps

* [Services](services.md)
* [Configuration](configuration.md)
* [Factory functions](factory_functions.md)
