Wireup can be used standalone as a DI container/service locator
or it can be integrated with common frameworks for simplified usage.

This guide will show you how to use the basics of the container
and will include links to the various integrations at the end.


## Guide

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
        "weather_api_key": os.environ["APP_WEATHER_API_KEY"]
    },
    # Top-level modules containing service registrations.
    service_modules=[services]
)

# Services are created on first use.
# If you want to create them ahead of time you can do so by using the warmup method.
container.warmup()
```

??? note "Read: Global variables"
    Using this approach means relying on global state, which ties your application to a single container instance. 
    This might be sufficient for you and that's okay but, if you want to avoid global state, it's better to create 
    the container within your application factory and provide a way to access it from the created application instance.

    With the available integrations, global state is neither necessary nor recommended.


### 2. Declare services

The container uses configuration metadata from decorators and annotations 
to define services and the dependencies between them. 
This means that the service declaration is self-contained and does not require additional setup for most use cases.


!!! tip "Use Wireup the way you prefer"
    The container can be configured through annotations or programmatically.
    It was designed with annotations in mind but all features are available with either approach. [Learn more](configuration.md).



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


1. Decorators are used to collect metadata. 
    This makes testing simpler, as you can still instantiate this like a regular class in your tests.
2. Parameters must be annotated with the `Inject(param=name)` syntax. This tells the container which parameter to inject.


```python title="services/weather_service.py" hl_lines="4 5"
@service
@dataclass # Use alongside dataclasses to simplify init code.
class WeatherService:
    api_key: Annotated[str, Inject(param="weather_api_key")]
    kv_store: KeyValueStore

    async def get_forecast(self, lat: float, lon: float) -> WeatherForecast:
        raise NotImplementedError
```


### 3. Use

Now you can use the container as a service locator or apply it as a decorator.

```python
weather_service = container.get(WeatherService)
```

```python title="views/posts.py"
@app.get("/weather/forecast")
@container.autowire
async def get_forecast_view(weather_service: WeatherService):
    return await weather_service.get_forecast(...)
```

### 4. Test

Wireup does not patch your services which means they can be instantiated and tested independently of the container.

To substitute dependencies on autowired targets such as views in a web application you can override dependencies with new ones on the fly.


```python
with container.override.service(WeatherService, new=test_weather_service):
    response = client.get("/weather/forecast")
```

Requests to inject `WeatherService` during the lifetime of the context manager 
will result in `test_weather_service` being injected instead.

## Conclusion

This concludes the "Getting Started" walkthrough, covering the most common dependency injection use cases.

!!! info "Good to know"
    * The `@container.autowire` decorator is not needed for services.
    * When using the provided integrations,
    decorating views with `@container.autowire` is no longer required.
    * Wireup can perform injection on both sync and async targets.
    * Every container you create is separate from the rest and has its own state.

## Next Steps

While Wireup is framework-agnostic, usage can be simplified when used with the following frameworks:

- [Django](integrations/django.md)
- [FastAPI](integrations/fastapi.md)
- [Flask](integrations/flask.md)


## Links

* [Services](services.md)
* [Configuration](configuration.md)
* [Factory functions](factory_functions.md)
