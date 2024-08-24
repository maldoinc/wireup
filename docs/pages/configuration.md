Wireup configuration can be injected through annotations or programmatically using factory functions. 
You can also mix and match the two as necessary.

## @ Annotations

This declarative approach uses configuration metadata provided by decorators and annotations to define services and dependencies between them.
It allows you to declare the final state and let the container handle the rest.

This generally results in less boilerplate code compared to a programmatic approach and is how many popular frameworks operate.


## 🏭 Programmatic

With a programmatic approach, you have full control over how services are created and can keep service
definitions devoid of container references if this is important to you.

This approach results in more code as you will need to write these factories and construct services yourself.

This will also be somewhat familiar if you're coming from FastAPI,
with the major difference being that you won't need to `Depends(get_service_from_function)` everywhere.

Factories can request dependencies as usual and may use annotations for configuration.

## @ Annotation-based configuration
In addition to service objects, the container also holds configuration, called parameters.

You can modify the parameters by updating the `container.params` dict.

!!! warning
    **Parameters represent application configuration**. 
    They are not intended to pass values around or to be used as a global session object.

    Store only app configuration such as environment name, database url, mailer url etc.

### Injection

#### By name

To inject a parameter by name, annotate the type with `Inject(param="param_name")`.

```python
@container.autowire
def target(cache_dir: Annotated[str, Inject(param="cache_dir")]) -> None:
    ...
```

```python
@service
class GithubClient:
    def __init__(self, api_key: Annotated[str, Inject(param="gh_api_key")]) -> None:
        ...
```

#### Parameter expressions

It is possible to interpolate parameters using a special syntax. This will enable you to retrieve several parameters at once and concatenate their values together.

**Note:** As the result is a string, non-string parameters will be converted using `str()`.

```python
@container.autowire
def target(logs_dir: Annotated[str, Inject(expr="${cache_dir}/${env}/logs")]) -> None:
    ...
```

## 🏭 Class-based configuration

While Wireup provides its own configuration mechanism in the form of parameters, it is entirely optional.
If you prefer using typed classes for configuration, they are also supported via factories.

The main idea is to register your settings as a service and inject it into factories like a regular dependency.

### Configuration

Assume your configuration is defined in an class such as this.
Examples use [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings) but any class will work exactly the same.



```python title="settings.py"
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn


class Settings(BaseSettings):
    gh_api_key: str = Field(alias="gh_api_key")  
    pg_dsn: PostgresDsn = Field(alias="pg_dsn")  
```

### Services
Next step would be to define a few services, such as `GithubClient` and a `DatabaseConnection`.

```python title="services/github_client.py"
@dataclass
class GithubClient:
    api_key: str

```

```python title="services/db.py"
@dataclass
class DatabaseConnection:
    dsn: str
```

### Factories

To wire everything together we can use a few factories.

```python title="factories.py"
from wireup import service, container

@service
def settings_factory() -> Settings:
    return Settings(...)


# Now that settings is registered with the container 
# it is possible to inject it like a regular service.
@service
def github_client_factory(settings: Settings) -> GithubClient:
    return GithubClient(api_key=settings.gh_api_key)


@service
def database_connection_factory(settings: Settings) -> DatabaseConnection:
    return DatabaseConnection(dsn=str(settings.pg_dsn))
```

