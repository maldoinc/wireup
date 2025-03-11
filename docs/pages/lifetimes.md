# Service Lifetimes

Wireup supports three different lifetimes for services: Singleton, Scoped, and Transient. The lifetime of a service
determines how long an instance of the service will live and is configured via the `lifetime` parameter in the `@service` decorator.

## Lifetimes Overview

### Singleton (default)

A singleton service is created once and shared throughout the application. Every request for this service will return the same instance.
This is useful for services that maintain state or are expensive to create.

```python
from wireup import service

@service
class SingletonService:
    ...

# Usage
s1 = container.get(SingletonService)
s2 = container.get(SingletonService)

# Both s1 and s2 refer to the same instance
assert s1 is s2
```

### Transient

A transient service creates a new instance every time it is requested. This is useful for stateless services or those that require a fresh state for each use.

```python
from wireup import service

@service(lifetime="transient")
class TransientService:
    ...

# Usage
t1 = container.get(TransientService)
t2 = container.get(TransientService)

# t1 and t2 are different instances
assert t1 is not t2
```

### Scoped

A scoped service is created once per scope and shared within that scope. The service instance will live as long as the scope does.
This is particularly useful in web applications where you want a service to live for the duration of a request.

```python
from wireup import service

@service(lifetime="scoped")
class ScopedService:
    ...

# Usage within a scope
with wireup.enter_scope(container) as scoped:
    s1 = container.get(SingletonService)
    s2 = scoped.get(SingletonService)

    # Singleton service remains the same across scopes
    assert s1 is s2

    sc1 = scoped.get(ScopedService)
    sc2 = scoped.get(ScopedService)

    # Scoped service remains the same within the same scope
    assert sc1 is sc2

# Usage across different scopes
with wireup.enter_scope(container) as scoped_a, wireup.enter_scope(container) as scoped_b:
    sc_a = scoped_a.get(ScopedService)
    sc_b = scoped_b.get(ScopedService)

    # Different scopes have different instances of ScopedService
    assert sc_a is not sc_b
```

!!! note
    Wireup integrations manage the scope lifecycle for you. 
    A new scope is entered at the beginning of a request and exited at the end. 
    This means that a `scoped` service will live for the duration of the request.