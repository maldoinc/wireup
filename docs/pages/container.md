The container manages application services and automatically resolves their dependencies. Create one at startup, register services, and let it handle the wiring.

## Creating Containers

Choose the container type based on the application's needs:

### Synchronous

For traditional synchronous Python applications:

```python
import wireup

container = wireup.create_sync_container(services=[UserService, Database])

user_service = container.get(UserService)
```

### Async

For applications using async/await:

```python
import wireup

container = wireup.create_async_container(services=[UserService, Database])

user_service = await container.get(UserService)
```

The async container can handle both sync and async services, but requires `await` for service retrieval.

## Registering Services

### 1. Service Discovery

Let Wireup automatically find services in modules:

```python
import wireup
from myapp import services, repositories

container = wireup.create_sync_container(
    service_modules=[services, repositories],
    config={"api_key": "secret"}
)
```

**Example project structure:**

```
myapp/
├── services/
│   ├── __init__.py
│   └── user_service.py      # Contains @service decorations
├── repositories/
│   ├── __init__.py
│   └── user_repository.py   # Contains @service decorations
└── main.py
```

**How it works:**

- Wireup scans the provided modules recursively
- Finds classes and functions decorated with `@service` or `@abstract`
- Automatically registers them and resolves their dependencies

### 2. Manual Registration

Register specific services individually:

```python
import wireup
from myapp.services import UserService, EmailService

container = wireup.create_sync_container(
    services=[UserService, EmailService],
    config={"db_url": "postgresql://localhost/myapp"}
)
```

You can also mix both approaches as needed:

```python
container = wireup.create_sync_container(
    service_modules=[services],      # Auto-discover
    services=[SpecialService],       # Manual addition
    config={"api_key": "secret"}
)
```

## Container Cleanup

Clean up the container when shutting down. This is required to properly close factories that manage resources.

```python
# For sync containers
container.close()

# For async containers
await container.close()
```
