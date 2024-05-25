<div align="center">
<h1>Wireup</h1>
<p>Modern Dependency Injection for Python.</p>

[![GitHub](https://img.shields.io/github/license/maldoinc/wireup)](https://github.com/maldoinc/wireup)
[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/maldoinc/wireup/run_all.yml)](https://github.com/maldoinc/wireup)
[![Code Climate maintainability](https://img.shields.io/codeclimate/maintainability/maldoinc/wireup?label=Code+Climate)](https://codeclimate.com/github/maldoinc/wireup)
[![Coverage](https://img.shields.io/codeclimate/coverage/maldoinc/wireup?label=Coverage)](https://codeclimate.com/github/maldoinc/wireup)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup)](https://pypi.org/project/wireup/)
[![PyPI - Version](https://img.shields.io/pypi/v/wireup)](https://pypi.org/project/wireup/)

<p>Wireup is a performant, concise, and easy to use dependency injection container for Python 3.8+.</p>
</div>

---

## ⚡ Key Features
* Inject Services and Configuration
* Interfaces/Abstract classes
* Factory pattern
* Singleton/Transient dependencies
* Framework Agnostic
* Simplified usage in [Django](https://maldoinc.github.io/wireup/latest/integrations/django/),
[Flask](https://maldoinc.github.io/wireup/latest/integrations/flask/) and 
[FastAPI](https://maldoinc.github.io/wireup/latest/integrations/fastapi/).

## 📋 Quickstart

Example showing a redis wrapper and a weather service which calls an external api and caches results as needed.

**1. Set up**

```python
from wireup import container, initialize_container
def create_app():
    app = ...
    
    # 👇 Expose configuration by populating container.params.
    container.params.put("redis_url", os.environ["APP_REDIS_URL"])
    container.params.put("weather_api_key", os.environ["APP_WEATHER_API_KEY"])

    # Bulk updating is possible via the "update" method.
    container.params.update(Settings().model_dump())
    
    # Start the container and register + initialize services
    # service_modules contains top-level modules containing registrations.
    initialize_container(container, service_modules=[services])

    return app
```


**2. Register services**

Use a declarative syntax to describe the services and let the container take care of the rest.

```python
from wireup import service, Inject

@service # 👈 Decorator lets the container know that this is a service.
class KeyValueStore:
                                           # This tells the container to pass the value 
                                           # of said parameter during creation.
                                           # 👇 
    def __init__(self, dsn: Annotated[str, Inject(param="redis_url")]):
        self.client = redis.from_url(dsn)

    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any): ...


@service
@dataclass
class WeatherService:
    # Pass the value of the parameter to this field. 👇
    api_key: Annotated[str, Inject(param="weather_api_key")]
    kv_store: KeyValueStore # 👈 This will be injected without having to specify additional metadata.

    def get_forecast(self, lat: float, lon: float) -> WeatherForecast:
        ...
```

**3. Inject**

Decorate targets where the library must perform injection. 

```python
from wireup import container

@app.get("/weather/forecast")
# 👇 Decorating views with autowire will make the container inject services/parameters.
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
