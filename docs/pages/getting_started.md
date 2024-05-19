This walkthrough will bring you up to speed with the most common use cases for a typical application.

We're going to build a simple weather forecast application that calls a remote weather service and 
uses a distributed key-value store to cache results.

## 1. Setup

Install wireup using pip or your favorite package manager.

```shell
$ pip install wireup
```

The first step is to set up the container. We do this by exposing configuration to the container on startup.
In this example, we will store the Redis URL and an API key for the weather service.


!!! Note "Configuration"
    Wireup can be configured to work through annotations or programmatically by using 
    factory functions. See [configuration docs](configuration.md) for more details.

    Sections below use tabs detailing how to achieve the result using each method.


=== "@ Annotations"
    ```python title="main.py" hl_lines="2 9 10 13 18"
    import os
    from wireup import container, warmup_container
    from myapp import services

    def create_app():
        app = ...
        
        # Expose configuration in the container by populating container.params.
        container.params.put("redis_url", os.environ["APP_REDIS_URL"])
        container.params.put("weather_api_key", os.environ["APP_WEATHER_API_KEY"])

        # Bulk updating is possible via the "update" method.
        container.params.update(Settings().model_dump())
        
        # Specify top-level modules containing registrations.
        # This will bring listed modules recursively into scope
        # and instantiate singleton services.
        warmup_container(container, service_modules=[services])

        return app
    ```

=== "🏭 Programmatic"
    ```python title="main.py" hl_lines="3 15 20"
    from pydantic import Field, PostgresDsn
    from pydantic_settings import BaseSettings
    from wireup import container, warmup_container

    from myapp.services import factories
    
    class Settings(BaseSettings):
        redis_url: str = Field(alias="APP_REDIS_URL")  
        weather_api_key: str = Field(alias="APP_WEATHER_API_KEY")  

    def create_app():
        app = ...
        
        # Expose configuration as a service which can then be inejcted.
        container.register(Settings)
        
        # Specify top-level modules containing registrations.
        # This will bring listed modules recursively into scope
        # and instantiate singleton services.
        warmup_container(container, service_modules=[factories])

        return app
    ```

Now that the setup is complete it's time to move on to the next step.

## 2. Define some services
### KeyValueStore

First, let's add a `KeyValueStore` service. We wrap Redis with a class that abstracts it. 

While we have the option to [inject Redis directly](factory_functions.md#inject-a-third-party-class), 
in this example, we've chosen the abstraction route. 

The Redis client requires specific configuration details to establish a connection to the server, 
which we fetch from the configuration.

=== "@ Annotations"

    !!! info
        Wireup performs automatic dependency discovery and most of the time you won't need to use annotations, however
        for parameters it is not possible to infer which one to inject solely from its type so additional metadata must
        be provided. [Learn more](annotations.md).

    Parameters must be annotated with the `Wire(param=name)` syntax. This tells the container which parameter to inject.
    
    ```python title="services/key_value_store.py" hl_lines="4 6"
    from wireup import service, Wire
    from typing_extensions import Annotated

    @service  #(1)!
    class KeyValueStore:
        def __init__(self, dsn: Annotated[str, Wire(param="redis_url")]) -> None:
            self.client = redis.from_url(dsn)

        def get(self, key: str) -> Any: ...
        def set(self, key: str, value: Any): ...
    ```

    Note: Wireup decorators and Annotations do not alter the class' behavior 
    and are only used to collect metadata.

    1. Decorators do not modify the classes in any way and only serve to collect metadata. This behavior can make
       testing a lot simpler as you can still instantiate this like a regular class in your tests.


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


    The `@service` decorator makes this factory known with the container.
    Return type is mandatory and denotes what will be built.

    ```python title="services/factories.py" hl_lines="3 4"
    from wireup import service

    @service
    def key_value_store_factory(settings: Settings) -> KeyValueStore:
        return KeyValueStore(dsn=settings.redis_url)
    ```

### WeatherService

Next, we add a new weather service that will perform requests against a remote server and cache results
as necessary.

=== "@ Annotations"

    The `api_key` will contain the value of the `weather_api_key` parameter as specified in the annotation and
    KeyValueStore will be automatically injected without requiring additional metadata.

    ```python title="services/weather.py" hl_lines="4 7 8"
    from wireup import service

    # Initializer injection is supported for regular classes as well as dataclasses.
    @service #(1)!
    @dataclass
    class WeatherService:
        api_key: Annotated[str, Wire(param="weather_api_key")]
        kv_store: KeyValueStore

        def get_forecast(self, lat: float, lon: float) -> WeatherForecast:
            # implementation omitted for brevity
            pass
    ```

    1.  * Injection is supported for regular classes as well as dataclasses.
        * When using dataclasses it is important that the dataclass decorator is applied before register.
    2.  * Use type hints to indicate which dependency to inject.
        * Dependencies are automatically discovered and injected.


    `KeyValueStore` gets automatically resolved by wireup and needs no additional metadata.


=== "🏭 Programmatic"

    ```python title="services/weather.py"
    @dataclass 
    class WeatherService:
        api_key: str
        kv: KeyValueStore

        def get_forecast(self, lat: float, lon: float) -> WeatherForecast:
            # implementation omitted for brevity
            pass
    ```

    ```python title="services/factories.py" hl_lines="3 4"
    from wireup import service

    @service
    def weather_service_factory(settings: Settings, kv_store: KeyValueStore) -> WeatherService:
        return WeatherService(api_key=settings.weather_api_key, kv=kv_store)
    ```


## 3. Inject

Decorate functions where the container needs to perform injection.


```python title="views/posts.py" hl_lines="2"
@app.get("/weather/forecast")
@container.autowire # (1)!
def get_forecast_view(weather_service: WeatherService):
    return weather_service.get_forecast(...)
```

1. Decorate methods where the library must perform injection.
   Optional when using the provided integrations.

## Conclusion

That was everything! Container knows how to build the services and they can be injected anywhere as necessary.

!!! info "Good to know"
    * You only need to call `@container.autowire` to inject targets that the container doesn't know about.
    * Although examples here show only sync code, Wireup can work on both sync and async functions.

## Links

* [Services](services.md)
* [Configuration](configuration.md)
* [Factory functions](factory_functions.md)
