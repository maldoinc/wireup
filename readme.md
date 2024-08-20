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
</div>

---

## ⚡ Key Features
* Inject services and configuration.
* Support for interfaces and abstract classes.
* Factory pattern.
* Singleton and transient dependencies.
* Framework-agnostic.
* Simplified integration with [Django](https://maldoinc.github.io/wireup/latest/integrations/django/),
[Flask](https://maldoinc.github.io/wireup/latest/integrations/flask/), and 
[FastAPI](https://maldoinc.github.io/wireup/latest/integrations/fastapi/).

## 📋 Quickstart

Example showcasing a Redis wrapper and a weather service that calls an external API and caches results as needed.

**1. Set up**

```python
import wireup

def create_app():
    app = ...

    wireup.initialize_container(
        wireup.container,
        # Top-level modules containing service registrations.
        # This is where your services live.
        service_modules=[services],
        # Parameters serve as application/service configuration.
        parameters={
            "redis_url": os.environ["APP_REDIS_URL"],
            "weather_api_key": os.environ["APP_WEATHER_API_KEY"]
        }
    )

    return app
```

**2. Register services**

Use a declarative syntax to describe services, and let the container handle the rest.

```python
from wireup import service, Inject

@service # ⬅️ Decorator tells the container this is a service.
class KeyValueStore:
                                           # This tells the container to inject the value
                                           # of the parameter during creation.
                                           # ⬇️ 
    def __init__(self, dsn: Annotated[str, Inject(param="redis_url")]):
        self.client = redis.from_url(dsn)

    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any): ...


@service
@dataclass
class WeatherService:
    # Inject the value of the parameter to this field. ⬇️
    api_key: Annotated[str, Inject(param="weather_api_key")]
    kv_store: KeyValueStore # ⬅️ This will be injected automatically without additional metadata.

    def get_forecast(self, lat: float, lon: float) -> WeatherForecast:
        ...
```

**3. Inject**

Decorate targets where the library should perform injection.

```python
from wireup import container

@app.get("/weather/forecast")
# ⬇️ Decorating views with autowire enables the container to inject services/parameters.
@container.autowire
def get_weather_forecast_view(weather_service: WeatherService, request):
    return weather_service.get_forecast(request.lat, request.lon)
```

**Installation**

```bash
# Install using poetry:
poetry add wireup

# Install using pip:
pip install wireup
```

## 📑 Documentation

For more information [check out the documentation](https://maldoinc.github.io/wireup)

## 🎮 Demo application

A demo flask application is available at [maldoinc/wireup-demo](https://github.com/maldoinc/wireup-demo)
