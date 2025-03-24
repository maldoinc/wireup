To showcase the basics of Wireup, we will create a container able to inject the following:

* A `WeatherService` that queries a fictional weather api. It needs an api key, a `KeyValueStore` to cache data and an async http client to make requests.
* `KeyValueStore` itself needs a `redis_url` denoting the server it will connect to to query/store data.

These services will then be retrieved in a `/weather/forecast` endpoint that requires `WeatherService` to provide weather information.

``` mermaid
graph LR
    redis_url[⚙️ redis_url] --> KeyValueStore[🐍 KeyValueStore]
    weather_api_key[⚙️ weather_api_key] --> WeatherService
    KeyValueStore --> WeatherService[🐍 WeatherService]
    WeatherService --> Route[🌎 /weather/forecast]
    F[🏭 HttpClient] --> WeatherService
```


!!! tip
    There will be little `+` icons in code fragments. You can click on those for more detailed
    information as to what is happening in that particular line.

### 1. Setup

Install wireup using pip or your favorite package manager.

```shell
$ pip install wireup
```

The first step is to create a container.

```python title="container.py"
import wireup

container = wireup.create_async_container(
    # Parameters are an optional key-value configuration store.
    # You can inject parameters as necessary by their name where required.
    parameters={ # (1)!
        "redis_url": os.environ["APP_REDIS_URL"],
        "weather_api_key": os.environ["APP_WEATHER_API_KEY"],
    },
    # Let the container know where service registrations are located.
    # This is a list of top-level modules Wireup should scan for service declarations.
    service_modules=[services]  # (2)!
)
```

1. Parameters are configuration your application needs.
    Such as an api key, database url, or other settings.

    You can inject them as necessary by their name (dict key) where required.
    Wireup won't pull things from the environment or other places for you.
    You need to expose to it the different settings you'll need.

    You don't have to use this if you prefer using things like pydantic-settings,
    but it will enable you to have self-contained service definitions without writing additional set-up code
    to create these objects.

    Note that the values can be literally anything you need to inject and not just int/strings or other scalars.
    You can put dataclasses for example in the parameters to inject structured configuration.

2.  Service modules is a list of top-level python modules containing service definitions this container
    needs to know about (Classes or functions decorated with `@service` or `@abstract`.).
    The container will only create types that are explicitly registered with it.


!!! note "Container variants: Sync and Async"
    Wireup includes two types of containers: async and sync. The difference is that the async one exposes
    `async def` methods for the common operations and is capable of creating resources from `async def` factories.

    The async container can create both regular and resources from async factories.

    If you don't use async in your code you should create a container via `wireup.create_sync_container`.
    Some integrations that Wireup provides also require you to create containers of a given type.
    E.g: FastAPI integration only supports async containers.


??? abstract "Read: Global variables"
    Using this approach means relying on global state, which ties your application to a single container instance. 
    This might be sufficient for you and that's okay but, if you want to avoid global state, it's better to create 
    the container within your application factory and store it in your application's state instead.


### 2. Define services

The container uses types and annotations to define services and the discover dependencies between them. This
results in self-contained


#### 🐍 `KeyValueStore`
To create `KeyValueStore`, all we need is the `redis_url` parameter.
The `@service` decorator tells Wireup this is a service, and we need to tell the container via annotated types
to fetch the value of the `redis_url` parameter for `dsn`. 


```python title="services/key_value_store.py" hl_lines="4 6"
from wireup import service, Inject
from typing_extensions import Annotated

@service  #(1)!
class KeyValueStore:
    def __init__(self, dsn: Annotated[str, Inject(param="redis_url")]) -> None:  #(2)!
        self.client = redis.from_url(dsn)
```

1. Decorators are only used to collect metadata. 
    This makes testing simpler, as you can still instantiate this like a regular class in your tests.
2. Since type-based injection is not possible here (there can be many string/int parameters after all), 
    parameters must be annotated with the `Inject(param=name)` syntax. This tells the container which parameter to inject.


#### 🏭 `aiohttp.ClientSession`

The http client making requests cannot be instantiated directly as we need to enter an async context manager.
To accommodate such cases, Wireup allows you to use functions to create dependencies. 
These can be sync/async as well as regular or generator functions if cleanup needs to take place.

Factories can define their dependencies in the function's signature.

!!! note ""
    When using generator factories make sure to call `container.close` when the application is terminating for the necessary cleanup to take place.

```python title="services/factories.py" hl_lines="1 2"
@service
async def make_http_client() -> AsyncIterator[aiohttp.ClientSession]:
    async with aiohttp.ClientSession() as client:
        yield client
```

#### 🐍 `WeatherService`
Creating `WeatherService` is also straightforward. The `@service` decorator is used to let Wireup know this is a service and we use the same syntax as above for the `api_key`. 

Class dependencies do not need additional annotations, even tough the http client is created via an async generator. This is transparently handled by the container.

```python title="services/weather_service.py" hl_lines="1 5 6 7"
@service
class WeatherService:
    def __init(
        self,
        api_key: Annotated[str, Inject(param="weather_api_key")], #(1)!
        kv_store: KeyValueStore, #(2)!
        client: aiohttp.ClientSession, #(3)!
    ) -> None: ...
```

1. Same as above, weather api key needs the parameter name for the container to inject it.
2. `KeyValueStore` can be injected only by type and does not require annotations.
3. `aiohttp.ClientSession` can be injected only by type and requires no additional configuration.


### 3. Use

All that's left now is to retrieve services from the container.


=== "Service Locator"

    To fetch services from the container, call `.get` on the container instance with the type you wish to retrieve.

    ```python title="views/posts.py"  hl_lines="3"
    @app.get("/weather/forecast")
    async def get_forecast():
        weather_service = await container.get(WeatherService)
        return await weather_service.get_forecast(...)
    ```

=== "Injection via decorator"

    You can also apply Wireup containers as decorators. See [Apply the container as a decorator](apply_container_as_decorator.md) docs for more info, but the end result is that you can
    decorate any function and specify dependencies to inject in it's signature.

    ```python title="views/posts.py"  hl_lines="4 5"
    from wireup import Injected, inject_from_container

    @app.get("/weather/forecast")
    @inject_from_container(container)
    async def get_forecast(weather_service: Injected[WeatherService]):
        return await weather_service.get_forecast(...)
    ```


=== "FastAPI"

    With the FastAPI integration you can just declare dependencies in http or websocket routes.

    ```python title="views/posts.py"  hl_lines="4"
    from wireup import Injected

    @app.get("/weather/forecast")
    async def get_forecast(weather_service: Injected[WeatherService]):
        return await weather_service.get_forecast(...)
    ```

    Learn More: [FastAPI Integration](integrations/fastapi.md).


=== "Flask"

    With the Flask integration you can just declare dependencies in views.

    ```python title="views/posts.py"  hl_lines="4"
    from wireup import Injected

    @app.get("/weather/forecast")
    async def get_forecast(weather_service: Injected[WeatherService]):
        return await weather_service.get_forecast(...)
    ```

    Learn More: [Flask Integration](integrations/flask.md).


=== "Django"

    With the Django integration you can just declare dependencies in views. The integration provides
    support for async views, regular views as well as class-based views.


    ```python title="views/posts.py"  hl_lines="4"
    from wireup import Injected

    async def get_forecast(weather_service: Injected[WeatherService]):
        return await weather_service.get_forecast(...)
    ```

    Learn More: [Django Integration](integrations/django.md).


#### 3.5 Integrate

While Wireup is framework-agnostic, usage can be simplified when using it alongside one of the integrations.
Key benefits of the integrations are:

* Automatic injection in routes without having to do `container.get` or use decorators.
* Lifecycle management and access to request-scoped dependencies.
* Eliminates the need for a global container variable as containers are bound to the application instance.
* Other goodies specific for that particular framework.

##### Integrations

- [x] [Django](integrations/django.md)
- [x] [FastAPI](integrations/fastapi.md)
- [x] [Flask](integrations/flask.md)

### 4. Test

Wireup does not patch your services, which means they can be instantiated and tested independently of the container.

To substitute dependencies on targets such as views in a web application you can override dependencies with new ones on the fly.


```python
with container.override.service(WeatherService, new=test_weather_service):
    response = client.get("/weather/forecast")
```

Requests to inject `WeatherService` during the lifetime of the context manager 
will result in `test_weather_service` being injected instead.

## Conclusion

This concludes the "Getting Started" walkthrough, covering the most common dependency injection use cases.

!!! info
    * Wireup can perform injection on both sync and async targets.
    * If you need to create multiple containers, every container you create is separate from the rest and has its own state.

## Next Steps

* [Services](services.md)
* [Parameters](parameters.md)
* [Factory functions](factory_functions.md)
