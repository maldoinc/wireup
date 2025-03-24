


# Service Lifetimes

Wireup manages how long service instances live through three different lifetimes: Singleton, Scoped, and Transient. Configure the lifetime using the `lifetime` parameter in the `@service` decorator.

## Available Lifetimes

### Singleton (Default)
One instance is created and shared across the entire application.

```python
@service  # lifetime="singleton" is the default
class Database: ...

# Same instance everywhere
db1 = container.get(Database)
db2 = container.get(Database)
assert db1 is db2
```

Best for:

* Stateful services.
* Resource-intensive services.
* Configuration holders.

### Scoped
One instance per scope, shared within that scope.

```python
@service(lifetime="scoped")
class RequestContext: ...

with container.enter_scope() as scope1, container.enter_scope() as scope2:
    # Same instance within scope
    ctx1 = scope1.get(RequestContext)
    ctx2 = scope1.get(RequestContext)
    assert ctx1 is ctx2

    # Different instance in different scope
    other = scope2.get(RequestContext)
    assert ctx1 is not other
```

Best for:

* Request-specific services.
* Per-operation state.
* Database transactions.

!!! info
    Wireup integrations manage the scope lifecycle for you. 
    A new scope is entered at the beginning of a request and exited at the end. 
    This means that a `scoped` service will live for the duration of the request.

    The Wireup `@wireup.inject_from_container(container)` decorator can also enter/exit a scope after the decorated function returns.
    [Learn More](apply_container_as_decorator.md).

### Transient
New instance created on every request.

```python
@service(lifetime="transient")
class MessageBuilder: ...

with container.enter_scope() as scope:
    # New instance every time
    builder1 = scope.get(MessageBuilder)
    builder2 = scope.get(MessageBuilder)
    assert builder1 is not builder2
```

Best for:

* Stateless services.
* Services that need fresh state.
* Temporary resources.

!!! warning "Scope Required"
    Transient services must be resolved within a scope, even if they don't use scoped dependencies.
    This ensures proper cleanup of resources if the transient service itself or one of its dependencies
    needs to perform cleanup.


## Lifetime Rules

* Singletons can depend only on other singletons.
* Scoped and transient services can depend on any lifetime.
* Parameters can be injected into all lifetimes.

!!! tip "Choosing a Lifetime"
    * Start with singleton unless you have a reason not to.
    * Use scoped for request-specific state.
    * Use transient for fresh instances or temporary resources.

#### Scoped services and decorated functions

Wireup lets you apply the container as a decorator. The provided integrations also decorate for you the routes/views
where Wireup services are used.

For such cases, you don't need to do any scope management yourself and can simply ask for the scoped/transient services
in the function's signature. The decorator can enter a scope and exit it once the function returns.