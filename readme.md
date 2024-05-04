<div align="center">
<h1>Wireup</h1>
<p>Modern Dependency Injection for Python.</p>

[![GitHub](https://img.shields.io/github/license/maldoinc/wireup)](https://github.com/maldoinc/wireup)
[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/maldoinc/wireup/run_all.yml)](https://github.com/maldoinc/wireup)
[![Code Climate maintainability](https://img.shields.io/codeclimate/maintainability/maldoinc/wireup?label=Code+Climate)](https://codeclimate.com/github/maldoinc/wireup)
[![Coverage](https://img.shields.io/codeclimate/coverage/maldoinc/wireup?label=Coverage)](https://codeclimate.com/github/maldoinc/wireup)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup)](https://pypi.org/project/wireup/)
[![PyPI - Version](https://img.shields.io/pypi/v/wireup)](https://pypi.org/project/wireup/)

<p>Wireup is a performant, concise and easy to use dependency injection container for Python 3.8+.</p>
</div>

---

## ⚡ Key Features
* Inject Services and Configuration
* Interfaces/Abstract classes
* Factory pattern
* Singleton/Transient dependencies
* Framework Agnostic
* Simplified usage in [Django](https://maldoinc.github.io/wireup/latest/integrations/flask/),
[Flask](https://maldoinc.github.io/wireup/latest/integrations/flask/) and 
[FastAPI](https://maldoinc.github.io/wireup/latest/integrations/fastapi/).

## 📋 Quickstart

Example showing a redis wrapper and a weather service which calls an external api and caches results as needed.

**1. Set up**

```python
from wireup import container, Wire
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


**2. Register dependencies**

```python
from wireup import container, Wire

@container.register 
class KeyValueStore:
    def __init__(self, dsn: Annotated[str, Wire(param="redis_url")]):
        self.client = redis.from_url(dsn)

    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any): ...
```       
Injection is supported for dataclasses as well

```python
@container.register
@dataclass
class WeatherService:
    api_key: Annotated[str, Wire(param="weather_api_key")]
    kv_store: KeyValueStore

    def get_forecast(self, lat: float, lon: float) -> WeatherForecast:
        ...
```

**3. Inject**

Decorate targets where the library must perform injection. 

```python
@app.get("/weather/forecast")
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
