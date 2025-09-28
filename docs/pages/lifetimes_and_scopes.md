# Lifetimes & Scopes

Wireup controls how long service instances live and when they're shared through **lifetimes** and **scopes**.

## Service Lifetimes

Configure how long service instances live using the `lifetime` parameter in the `@service` decorator.

### Singleton (Default)

One instance is created and shared across the entire application:

```python
@service  # lifetime="singleton" is the default
class Database:
    def __init__(self): ...

# Same instance everywhere
db1 = container.get(Database)  # Instance created
db2 = container.get(Database)  # Reuses instance
assert db1 is db2  # True
```

### Scoped

One instance per scope, shared within that scope:

```python
@service(lifetime="scoped")
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
@service(lifetime="transient")
class MessageBuilder:
    def __init__(self):
        self.timestamp = time.time()

with container.enter_scope() as scope:
    builder1 = scope.get(MessageBuilder)
    builder2 = scope.get(MessageBuilder)
    assert builder1 is not builder2  # Always different instances
```

!!! note "Scope Required"
    Only singletons may be resolved using the base container instance. Scoped and Transient dependencies must
    be resolved within a scope to ensure proper cleanup of resources.

    Singleton dependencies will be cleaned up when the container's `.close()` method is called.

## Lifetime Summary

| Lifetime  | Instance Creation  | Shared Within      | Best For                                     |
| --------- | ------------------ | ------------------ | -------------------------------------------- |
| Singleton | Once per container | Entire application | Configuration, database connections, caching |
| Scoped    | Once per scope     | Current scope only | Request state, transactions, user sessions   |
| Transient | Every resolution   | Never shared       | Stateless services, temporary objects        |

## Working with Scopes

Scopes provide isolated dependency contexts, particularly useful for web applications where you want fresh instances per request.

### Creating Scopes

=== "Synchronous"
    ```python
    container = wireup.create_sync_container(services=[RequestService])

    with container.enter_scope() as scoped_container:
        service1 = scoped_container.get(RequestService)
        service2 = scoped_container.get(RequestService)
        # service1 and service2 are the same instance (if scoped lifetime)

    with container.enter_scope() as another_scope:
        service3 = another_scope.get(RequestService)
        # service3 is a different instance from service1/service2
    ```

=== "Asynchronous"
    ```python
    container = wireup.create_async_container(services=[RequestService])

    async with container.enter_scope() as scoped_container:
        service1 = await scoped_container.get(RequestService)
        service2 = await scoped_container.get(RequestService)
    ```

### Automatic Scope Management

**Web Framework Integrations:**

The provided [integrations](integrations/index.md) automatically create a scope for every request.

```python
@app.get("/users/me")
def get_current_user(auth: Injected[AuthService]):
    return auth.current_user()  # Fresh scoped services per request
```

**Function Decorator:**

The [`@wireup.inject_from_container`](apply_container_as_decorator.md) decorator will also enter a new scope if none is provided in the parameters.

```python
@wireup.inject_from_container(container)
def process_order(order_service: OrderService):
    # Scope automatically created and cleaned up
    return order_service.process()
```

### Resource Cleanup

Scoped containers automatically clean up resources when the scope exits:

```python
@service(lifetime="scoped")
def database_session() -> Iterator[Session]:
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

with container.enter_scope() as scope:
    session = scope.get(Session)
    # session.close() is automatically called when exiting this "with" block
```

When using [generator factories](factories.md#error-handling) with scoped lifetime, errors that occur anywhere within the scope are automatically propagated to the factories for proper error handling like rolling back database transactions.

## Dependency Rules & Choosing Lifetimes

Services have restrictions on what they can depend on based on their lifetime:

- **Singletons** can only depend on other singletons and parameters
- **Scoped** services can depend on singletons, other scoped services, and parameters  
- **Transient** services can depend on any lifetime and parameters
