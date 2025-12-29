If you prefer not to add Wireup annotations to your classes and keep domain logic free of infrastructure concerns,
you can use factories to create all services including configuration.

## Using Factory Functions

Instead of decorating classes directly, create factories that create said classes.

```python title="services.py"
# Clean domain objects - no annotations
class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

class UserRepository:
    def __init__(self, database: Database) -> None:
        self.database = database
```

```python title="factories.py"
from wireup import service

@service
def user_repository_factory(database: Database) -> UserRepository:
    return UserRepository(database)

@service  
def user_service_factory(repository: UserRepository) -> UserService:
    return UserService(repository)
```

## Configuration Classes

For deeply nested configuration, consider using typed classes instead of configuration injection:

```python title="factories.py"
from wireup import service

# Register configuration
@service
def app_config_factory() -> AppConfig:
    return AppConfig(
        database=DatabaseConfig(...),
        redis=RedisConfig(...),
        api_key=...,
    )

@service
def database_factory(config: AppConfig) -> Database:
    return Database(config.database)

@service
def redis_factory(config: AppConfig) -> Redis:
    return Redis(config.redis.url, timeout=config.redis.timeout)
```