The container manages application objects and automatically resolves their dependencies. Create one at startup, register injectables, and let it handle the wiring.

## Creating Containers

Choose the container type based on the application's needs:

### Synchronous

For traditional synchronous Python applications:

```python
import wireup

container = wireup.create_sync_container(injectables=[UserService, Database])

user_service = container.get(UserService)
```

### Async

For applications using async/await:

```python
import wireup

container = wireup.create_async_container(injectables=[UserService, Database])

user_service = await container.get(UserService)
```

The async container can handle both sync and async injectables, but requires `await` for retrieval.

## Registering Injectables

### 1. Injectable Discovery

Let Wireup automatically find injectables in modules:

```python
import wireup
from myapp import services, repositories

container = wireup.create_sync_container(
    injectables=[services, repositories],
    config={"api_key": "secret"}
)
```

**Example project structure:**

```
myapp/
├── services/
│   ├── __init__.py
│   └── user_service.py      # Contains @injectable decorations
├── repositories/
│   ├── __init__.py
│   └── user_repository.py   # Contains @injectable decorations
└── main.py
```

**How it works:**

- Wireup scans the provided modules recursively
- Finds classes and functions decorated with `@injectable` or `@abstract`
- Automatically registers them and resolves their dependencies

### 2. Manual Registration

Register specific injectables individually:

```python
import wireup
from myapp.services import UserService, EmailService

container = wireup.create_sync_container(
    injectables=[UserService, EmailService],
    config={"db_url": "postgresql://localhost/myapp"}
)
```

You can also mix both approaches as needed:

```python
container = wireup.create_sync_container(
    injectables=[services, SpecialService],  # Auto-discover and Manual addition
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
