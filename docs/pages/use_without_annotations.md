Wireup uses types, annotations, and decorators to manage dependencies, allowing you to write self-contained services.
All the information needed to build a service is included and evolves with the service, reducing boilerplate by eliminating the need for factories for every service.

If you prefer not to use annotations, you can use factories to create everything.


### Configuration

The example below uses class-based configuration using `pydantic-settings`, but any class configuration method will work similarly.
This lets you bring your own configuration and replace Wireup parameters if they're not suitable for your project.

```python title="settings.py"
from pydantic_settings import BaseSettings, Field

@dataclass
class Settings(BaseSettings):
    gh_api_key: str = Field(alias="gh_api_key")  
    pg_dsn: PostgresDsn = Field(alias="pg_dsn")  
```

### Services

Next, define services like `GithubClient` and `DatabaseConnection`.

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

Use factories to wire everything together.

```python title="factories.py"
from wireup import service, container

@service
def settings_factory() -> Settings:
    return Settings()

# With settings registered in the container, it can be injected like a regular service.
@service
def github_client_factory(settings: Settings) -> GithubClient:
    return GithubClient(api_key=settings.gh_api_key)

@service
def database_connection_factory(settings: Settings) -> DatabaseConnection:
    return DatabaseConnection(dsn=str(settings.pg_dsn))
```