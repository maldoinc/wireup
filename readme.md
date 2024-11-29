<div align="center">
<h1>Wireup</h1>
<p>Modern Dependency Injection for Python.</p>

[![GitHub](https://img.shields.io/github/license/maldoinc/wireup)](https://github.com/maldoinc/wireup)
[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/maldoinc/wireup/run_all.yml)](https://github.com/maldoinc/wireup)
[![Code Climate maintainability](https://img.shields.io/codeclimate/maintainability/maldoinc/wireup?label=Code+Climate)](https://codeclimate.com/github/maldoinc/wireup)
[![Coverage](https://img.shields.io/codeclimate/coverage/maldoinc/wireup?label=Coverage)](https://codeclimate.com/github/maldoinc/wireup)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup)](https://pypi.org/project/wireup/)
[![PyPI - Version](https://img.shields.io/pypi/v/wireup)](https://pypi.org/project/wireup/)

<p>Wireup is a performant, concise, and easy-to-use dependency injection container for Python 3.8+.</p>
<p><a target="_blank" href="https://maldoinc.github.io/wireup">📚 Documentation</a> | <a target="_blank" href="https://github.com/maldoinc/wireup-demo">🎮 Demo Application</a></p>
</div>

---

## ⚡ Key Features
* Inject services and configuration.
* Interfaces and abstract classes.
* Factory pattern.
* Singleton and transient dependencies.
* Framework-agnostic.
* Apply the container as a decorator.
* Service Locator.
* Simplified use with [Django](https://maldoinc.github.io/wireup/latest/integrations/django/),
[Flask](https://maldoinc.github.io/wireup/latest/integrations/flask/), and 
[FastAPI](https://maldoinc.github.io/wireup/latest/integrations/fastapi/).
* Share service layer between cli and api.

## 📋 Quickstart

**1. Set up**

```python
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
```

**2. Declare services**

Use a declarative syntax to describe services, and let the container handle the rest.

```python
from wireup import service, Inject

@service # ⬅️ Decorator tells the container this is a service.
class KeyValueStore:
    # Inject the value of the parameter during creation. ⬇️ 
    def __init__(self, dsn: Annotated[str, Inject(param="redis_url")]):
        self.client = redis.from_url(dsn)

    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any): ...


@service
@dataclass # Can be used alongside dataclasses to simplify init boilerplate.
class WeatherService:
    # Inject the value of the parameter to this field. ⬇️
    api_key: Annotated[str, Inject(param="weather_api_key")]
    kv_store: KeyValueStore # ⬅️ This will be injected automatically.

    def get_forecast(self, lat: float, lon: float) -> WeatherForecast:
        ...
```

Use factories (sync and async) if service requires special initialization or cleanup.

```python
@service
async def make_db(dsn: Annotated[str, Inject(param="db_dsn")]) -> AsyncIterator[Connection]:
    async with Connection(dsn) as conn:
        yield conn
```

*Note*: If you use generator factories, call `container.{close,aclose}` on termination for the necessary cleanup to take place.


**3. Use**

Use the container as a service locator or apply it as a decorator to have it perform injection.

```python
weather_service = container.get(WeatherService)
```

```python
@app.get("/weather/forecast")
# ⬇️ Decorate functions to perform Dependency Injection.
# No longer required when using the provided integrations.
@container.autowire
def get_weather_forecast_view(weather_service: WeatherService, request):
    return weather_service.get_forecast(request.lat, request.lon)
```

**4. Test**

Wireup does not patch your services which means they can be instantiated and tested independently of the container.

To substitute dependencies on autowired targets such as views in a web application you can override dependencies with new ones on the fly.

```python
with container.override.service(WeatherService, new=test_weather_service):
    response = client.get("/weather/forecast")
```

Requests to inject `WeatherService` during the lifetime of the context manager 
will result in `test_weather_service` being injected instead.

## Share service layer betwen app/api and cli

Many projects have a web application as well as a cli in the same project which
provides useful commands.

Wireup makes it extremely easy to share the service layer between them without
code duplication. For examples refer to [maldoinc/wireup-demo](https://github.com/maldoinc/wireup-demo).

## Installation

```bash
# Install using poetry:
poetry add wireup

# Install using pip:
pip install wireup
```

## 📚 Documentation

For more information [check out the documentation](https://maldoinc.github.io/wireup)

## 🎮 Demo application

A demo flask application is available at [maldoinc/wireup-demo](https://github.com/maldoinc/wireup-demo)

## Limitations

Due to reliance on type hints, `from __future__ import annotations` should not be used on files
that the container should interact with. This includes files that explicitly use wireup annotations or decorators
as well injection targets.

This is expected to be fixed once `typing_extensions` 4.13 lands which includes relevant backports.