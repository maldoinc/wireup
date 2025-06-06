# Wireup vs FastAPI Dependency Injection

This document compares Wireup's dependency injection capabilities with FastAPI's built-in dependency injection system.

## Key Differences

### Performance 

Wireup's DI system is up to 2.7x faster than FastAPI's built-in dependency injection:

**Benchmark Results** (10,000 requests, single worker, best of 5):

| Implementation   | Requests/sec | Time (s) | % Slower than baseline |
| ---------------- | ------------ | -------- | ---------------------- |
| Baseline         | 12,183       | 0.82     | 0%                     |
| Wireup Zero-Cost | 12,182       | 0.82     | 0%                     |
| Wireup           | 10,195       | 0.98     | 19%                    |
| FastAPI Depends  | 4,484        | 2.23     | 172%                   |

### Type Safety & Early Validation

- **Type Checking**: Full mypy compliance ensures dependency errors are caught during development
- **Startup Validation**: Missing or misconfigured dependencies are detected when the application starts
- **Concise Service Declaration**: Reduced boilerplate for service definition and injection.

```python title="Wireup"
# ✅ Wireup - Concise, Type safe, catches errors early.
@service
class UserService:
    def __init__(self, db: Database, cache: Cache) -> None:
        self.db = db 
        self.cache = cache
```

```python title="FastAPI"
# ❌ FastAPI - Runtime errors, no startup validation
class UserService:
    def __init__(self, db: Database, cache: Cache) -> None:
        self.db = db 
        self.cache = cache

def get_user_service(
    db: Annotated[Database, Depends(get_database)],
    cache: Annotated[Cache, Depends(get_cache)]
):
    return UserService(db, cache)
```

### Service Management

- **Lifetime Control**: Singleton, scoped and transient services with proper cleanup
- **Async & Generator Support**: First-class support for async services and cleanup via generators 
- **Framework Independence**: Services can be shared between web app, CLI and other interfaces

```python
# Wireup - Clean service definitions with lifetime control
@service(lifetime="scoped")  # One per request
class RequestContext:
    def __init__(self, cache: Cache) -> None:
        self.request_id = uuid4()

# FastAPI - Manual scope management required
def get_request_context(
    cache: Annotated[Cache, Depends(get_cache)]
) -> RequestContext:
    return RequestContext(cache)
```
