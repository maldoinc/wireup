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
* Apply the container anywhere as a decorator.
* Service Locator.
* Simplified use with [Django](https://maldoinc.github.io/wireup/latest/integrations/django/),
[Flask](https://maldoinc.github.io/wireup/latest/integrations/flask/), and 
[FastAPI](https://maldoinc.github.io/wireup/latest/integrations/fastapi/).
* Share service layer between cli and api.

## 📋 Quickstart

Example showcasing a Redis wrapper and a weather service that calls an external API and caches results as needed.

**1. Set up**

```python
from wireup import container, initialize_container

def create_app():
    app = ...

    # ⬇️ Start the container: Register and initialize services.
    initialize_container(
        container,
        # Parameters serve as application/service configuration.
        parameters={
            "redis_url": os.environ["APP_REDIS_URL"],
            "weather_api_key": os.environ["APP_WEATHER_API_KEY"]
        },
        # Top-level modules containing service registrations.
        service_modules=[services]
    )

    return app
```

**2. Register services**

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

**3. Inject**

Decorate targets where the library should perform injection.

```python
from wireup import container
@app.get("/weather/forecast")
# ⬇️ Decorate functions to perform Dependency Injection.
# Optional in views with Flask or FastAPI integrations.
@container.autowire
def get_weather_forecast_view(weather_service: WeatherService, request):
    return weather_service.get_forecast(request.lat, request.lon)
```

## Share service layer betwen app/api and cli

Many projects have a web application as well as a cli in the same project which
provides useful commands.

Wireup makes it extremely easy to share the service layer between them without
code duplication.

### Flask + Click

Extract from [maldoinc/wireup-demo](https://github.com/maldoinc/wireup-demo),
showing the same service being used in a Flask view as well as in a Click command.
Imports omitted for brevity.


**App/Api**

With the Flask integration, `@container.autowire` can be omitted.


```python
# blueprints/post.py
@bp.post("/")
def create_post(post_service: PostService) -> Response:
    new_post = post_service.create_post(PostCreateRequest(**flask.request.json))

    return jsonify(new_post.model_dump())
```

**Click CLI**

```python
# commands/create_post_command.py
@click.command()
@click.argument("title")
@click.argument("contents")
@container.autowire
def create_post(title: str, contents: str, post_service: PostService) -> None:
    post = post_service.create_post(
        PostCreateRequest(
            title=title, 
            content=contents, 
            created_at=datetime.now(tz=timezone.utc)
        )
    )

    click.echo(f"Created post with id: {post.id}")

@click.group()
def cli() -> None:
    pass


if __name__ == "__main__":
    cli.add_command(create_post)
    initialize_container(
        container, 
        parameters=get_config(), 
        service_modules=[services]
    )
    cli()
```

**Typer CLI**

Typer functions a bit differently in that it won't allow unknown arguments
in the function signature, so we have to use the wireup container as a service locator.

```python
cli = typer.Typer()

@cli.command()
def create_post(title: str, contents: str) -> None:
    # Using container.get(T) returns an instance of that type.
    post = container.get(PostService).create_post(
        PostCreateRequest(
            title=title, 
            content=contents, 
            created_at=datetime.now(tz=timezone.utc)
        )
    )

    typer.echo(f"Created post with id: {post.id}")


if __name__ == "__main__":
    initialize_container(wireup.container, service_modules=[services], parameters=get_config())
    cli()
```

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
