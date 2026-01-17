Wireup controls how long injectable instances live and when they're shared through **lifetimes** and **scopes**.

## Injectable Lifetimes

Configure how long injectable instances live using the `lifetime` parameter in the `@injectable` decorator.

### Singleton (Default)

One instance is created and shared across the entire application:

```python
@injectable  # lifetime="singleton" is the default
class Database:
    def __init__(self): ...


# Same instance everywhere
db1 = container.get(Database)  # Instance created
db2 = container.get(Database)  # Reuses instance
assert db1 is db2  # True
```

!!! tip
    Singletons are lazy by default. See [Eager Initialization](container.md#eager-initialization) to initialize them at
    startup.

### Scoped

One instance per scope, shared within that scope:

```python
@injectable(lifetime="scoped")
class RequestContext:
    def __init__(self):
        self.request_id = uuid.uuid4()


with container.enter_scope() as scope1:
    ctx1 = scope1.get(RequestContext)
    ctx2 = scope1.get(RequestContext)
    assert ctx1 is ctx2  # Same instance within scope

with container.enter_scope() as scope2:
    ctx3 = scope2.get(RequestContext)
    assert ctx1 is not ctx3  # Different instance in different scope
```

### Transient

Creates a new instance on every resolution:

```python
@injectable(lifetime="transient")
class MessageBuilder:
    def __init__(self):
        self.timestamp = time.time()


with container.enter_scope() as scope:
    builder1 = scope.get(MessageBuilder)
    builder2 = scope.get(MessageBuilder)
    assert builder1 is not builder2  # Always different instances
```

!!! note "Scope Required"
    Only singletons may be resolved using the root container instance. Scoped and Transient dependencies must be resolved
    within a scope to ensure proper cleanup of resources.

    Singleton dependencies will be cleaned up when the root container's `.close()` method is called. Transient dependencies
    are cleaned up when the **scope that created them** closes.

## Lifetime Summary

| Lifetime  | Instance Creation  | Shared Within      | Best For                                     |
| --------- | ------------------ | ------------------ | -------------------------------------------- |
| Singleton | Once per container | Entire application | Configuration, database connections, caching |
| Scoped    | Once per scope     | Current scope only | Request state, transactions, user sessions   |
| Transient | Every resolution   | Never shared       | Stateless objects, temporary objects         |

## Working with Scopes

Scopes provide isolated contexts. This is useful for things like database sessions or user context that should only
exist for a short duration (like a single HTTP request).

=== "Web Frameworks"
    When using [Integrations](integrations/index.md) (like FastAPI, Flask, Django), **scopes are handled automatically**. A
    new scope is created for every incoming request and closed when the request finishes.

    ```python
    @app.get("/users/me")
    def get_current_user(auth_service: Injected[AuthService]):
        return auth_service.get_current_user()
    ```

=== "Function Decorator"
    The [`@wireup.inject_from_container`](function_injection.md) automatically enters a new scope before the function runs
    and closes it afterwards, ensuring cleanup is performed.

    ```python
    @wireup.inject_from_container(container)
    def process_order(order_service: Injected[OrderService]):
        return order_service.process()
    ```

=== "Manual Context"
    For granular control, you can manage scopes manually using `container.enter_scope()`.

    **Synchronous**

    ```python
    container = wireup.create_sync_container(injectables=[RequestService])

    with container.enter_scope() as scope:
        # Resolve dependencies from this specific scope
        service = scope.get(RequestService)
        service.process()

    # When the block exits, the scope is closed and cleanup runs.
    ```

    **Asynchronous**

    ```python
    container = wireup.create_async_container(injectables=[RequestService])

    async with container.enter_scope() as scope:
        service = await scope.get(RequestService)
        service.process()
    ```

### Resource Cleanup

Scoped containers ensure that resources are released when the scope exits. This simplifies resource management for
things like database transactions or file handles.

See [Resources & Cleanup](resources.md) for details on creating cleanable resources using generator factories.

## Lifetime Rules

### Lifetime Rules

Injectables have restrictions on what they can depend on to prevent **Scope Leakage**:

- **Singletons** can only depend on other singletons and config.
    - *Why?* A Singleton is alive for the duration of the application. If it depended on a short-lived object (Scoped or
        Transient), that object would be kept alive indefinitely, preventing cleanup and causing memory leaks. Wireup
        prevents this common pitfall by design.
- **Scoped** can depend on singletons, scoped, and config.
- **Transient** can depend on any lifetime and config.

## Next Steps

- [Factories](factories.md) - Create complex injectables with setup and teardown logic.
- [Interfaces](interfaces.md) - Register multiple implementations of the same type.
- [Testing](testing.md) - Override dependencies for testing.
