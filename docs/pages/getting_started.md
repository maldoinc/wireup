This walkthrough will introduce you to the most common use cases for a typical application. 

We'll build a simple weather forecast application that calls a remote weather service 
and uses a distributed key-value store to cache results.


## 1. Setup

### Installation

Install wireup using pip or your favorite package manager.

```shell
$ pip install wireup
```

### Configuration

!!! tip "Use Wireup the way you prefer"
    The container can be configured through annotations or programmatically.
    It was designed with annotations in mind but all features are available with either approach.

    Sections below show how to achieve the same result using each method. [Learn more](configuration.md).

The first step is to set up the container by exposing configuration on startup.
In this example, we will store the Redis URL and an API key for the weather service.

=== "@ Annotations"

    ```python title="main.py" hl_lines="9 10 13 17"
    import os
    from wireup import container, initialize_container
    from myapp import services

    def create_app():
        app = ...
        
        # Expose configuration by populating container.params.
        container.params.put("redis_url", os.environ["APP_REDIS_URL"])
        container.params.put("weather_api_key", os.environ["APP_WEATHER_API_KEY"])

        # Bulk update is also possible.
        container.params.update(Settings().model_dump())
        
        # Start the container: This registers + initializes services.
        # `service_modules` contains top-level modules containing registrations.
        initialize_container(container, service_modules=[services])

        return app
    ```

=== "🏭 Programmatic"
    ```python title="main.py" hl_lines="15 19"
    from pydantic import Field, PostgresDsn
    from pydantic_settings import BaseSettings
    from wireup import container, initialize_container

    from myapp.services import factories
    
    class Settings(BaseSettings):
        redis_url: str = Field(alias="APP_REDIS_URL")  
        weather_api_key: str = Field(alias="APP_WEATHER_API_KEY")  

    def create_app():
        app = ...f
        
        # Expose configuration as a service in the container.
        container.register(Settings)
        
        # Start the container: This registers + initializes services
        # service_modules contains top-level modules containing registrations.
        initialize_container(container, service_modules=[factories])

        return app
    ```

Now that the setup is complete, let's move on to the next step.

## 2. Define services
### KeyValueStore

First, let's add a `KeyValueStore` service. We wrap Redis with a class that abstracts it. 

While we have the option to [inject Redis directly](factory_functions.md#inject-a-third-party-class), 
in this example, we've chosen the abstraction route. 

The Redis client requires specific configuration details to establish a connection with the server,
which we fetch from the configuration.

=== "@ Annotations"
    With a declarative approach, the container uses configuration metadata 
    provided from decorators and annotations to define services and the dependencies between them. 
    This means that the service declaration is self-contained and does not require additional setup.

    ```python title="services/key_value_store.py" hl_lines="4 6"
    from wireup import service, Inject
    from typing_extensions import Annotated

    @service  #(1)!
    class KeyValueStore:
        def __init__(self, dsn: Annotated[str, Inject(param="redis_url")]) -> None:  #(2)!
            self.client = redis.from_url(dsn)

        def get(self, key: str) -> Any: ...
        def set(self, key: str, value: Any): ...
    ```

    1. Decorators do not modify the classes in any way and only serve to collect metadata. 
       This makes testing simpler, as you can still instantiate this like a regular class in your tests.
    2. Parameters must be annotated with the `Inject(param=name)` syntax. This tells the container which parameter to inject.
    
    The `@service` decorator marks this class as a service to be registered in the container.
    Decorators and annotations are read once during the call to `initialize_container`.

=== "🏭 Programmatic"
    With this approach, services are devoid of container references. 
    Registration and creation is handled by factory functions.

    ```python title="services/key_value_store.py"
    class KeyValueStore:
        def __init__(self, dsn: str) -> None:
            self.client = redis.from_url(dsn)

        def get(self, key: str) -> Any: ...
        def set(self, key: str, value: Any): ...
    ```

    The `@service` decorator makes this factory known with the container.. Decorators/annotations
    are read once during the call to `initialize_container`. 
    Return type is mandatory and denotes what will be built.

    ```python title="services/factories.py" hl_lines="3 4"
    from wireup import service

    @service
    def key_value_store_factory(settings: Settings) -> KeyValueStore:
        return KeyValueStore(dsn=settings.redis_url)
    ```

### WeatherService

Next, we add a weather service that will perform requests against a remote server and cache results as necessary.

=== "@ Annotations"

    The `api_key` field contains the value of the `weather_api_key` parameter as specified in the annotation. 
    `KeyValueStore` will be automatically injected without requiring additional metadata.

    ```python title="services/weather.py" hl_lines="3 6 7"
    from wireup import service

    @service #(1)!
    @dataclass
    class WeatherService:
        api_key: Annotated[str, Inject(param="weather_api_key")]
        kv_store: KeyValueStore

        async def get_forecast(self, lat: float, lon: float) -> WeatherForecast:
            # implementation omitted for brevity
            pass
    ```

    1.  * Injection is supported for regular classes as well as dataclasses.
        * When using dataclasses it is important that the `@dataclass` decorator is applied before `@service`.
    2.  * Use type hints to indicate which dependency to inject.
        * Dependencies are automatically discovered and injected.

=== "🏭 Programmatic"

    ```python title="services/weather.py"
    @dataclass 
    class WeatherService:
        api_key: str
        kv: KeyValueStore

        async def get_forecast(self, lat: float, lon: float) -> WeatherForecast:
            # implementation omitted for brevity
            pass
    ```

    ```python title="services/factories.py" hl_lines="3 4"
    from wireup import service

    @service
    def weather_service_factory(settings: Settings, kv_store: KeyValueStore) -> WeatherService:
        return WeatherService(api_key=settings.weather_api_key, kv=kv_store)
    ```

That concludes service creation. The container knows how to build services and inject them as necessary.

## 3. Inject

The final step would be to decorate functions where the container needs to perform injection.
Decorate injection targets with `@container.autowire`.


```python title="views/posts.py" hl_lines="2"
@app.get("/weather/forecast")
@container.autowire # (1)!
async def get_forecast_view(weather_service: WeatherService):
    return await weather_service.get_forecast(...)
```

1. Decorate methods where the library must perform injection.

## Conclusion

This concludes the "Getting Started" walkthrough, covering the most common dependency injection use cases.

!!! info "Good to know"
    * The `@container.autowire` decorator is not needed for services.
    * Wireup can perform injection on both sync and async functions.

## Links

* [Services](services.md)
* [Configuration](configuration.md)
* [Factory functions](factory_functions.md)
