Wireup supports three different lifetimes: Singletons, Scoped and Transient.

This dictates how long each service instance will live. The lifetime of a service is configured
via the `lifetime` parameter in the `@service` decorator.

## Lifetimes by example

Take the following services.

```python
@service
class SingletonService: ...

@service(lifetime="transient")
class TransientService: ...

@service(lifetime="scoped")
class ScopedService: ...
```

### Singleton (default)
The container will create only one copy of this service. Every time you request it,
you will get the same instance. Useful for cases where the class holds state or is expensive
to create.

```python
s1 = container.get(SingletonService)
s2 = container.get(SingletonService)

# As this is a singleton all calls resolve to the same instance.
assert s1 is s2
```

### Transient 
Every time you request a transient service, you will receive a new instance.
This is useful for classes where the functionality provided requires a clean state.

```python
t1 = container.get(TransientService)
t2 = container.get(TransientService)

# T1 and T2 are different since transient services will always return a fresh instance.
assert t1 is not t2
```


### Scoped
The container will create only one copy of this service for each scope and the services will live as long as the scope does.

```python
with wireup.enter_scope(container) as scoped:
    s1 = container.get(SingletonService)
    s2 = scoped.get(SingletonService)

    # The scoped container will also return the same instance of a singleton.
    assert s1 is s2

    sc1 = scoped.get(ScopedService)
    sc2 = scoped.get(ScopedService)

    # The scoped container will reuse the same instance for the duration of the scope.
    assert sc1 is sc2
```

Assume two concurrent scoped containers are in operation (e.g.: One for each http request).

```python
with wireup.enter_scope(container) as scoped_a, wireup.enter_scope(container) as scoped_b:
    sc_a = scoped_a.get(ScopedService)
    sc_b = scoped_b.get(ScopedService)

    # Each scoped container will have its own instance of the ScopedService.
    assert sc_a is not sc_b
```