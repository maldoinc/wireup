!!! note
    When using the provided integrations, this is automatically handled for you.
    Only use this if you're injecting Wireup dependencies in a framework without an integration.

Instead of manually retrieving services via `container.get` or parameters via `container.params`, you can inject them directly into function parameters using the container as a decorator.

This transforms verbose manual dependency retrieval:

```python
def client_function() -> None:
    random = container.get(RandomService)
    env_name = container.params.get("env")

    with container.enter_scope() as scoped_container:
        scoped_service = scoped_container.get(ScopedService)
```

Into clean, declarative dependency injection.

## Using `@wireup.inject_from_container`

Use the `wireup.inject_from_container` decorator to automatically inject dependencies into function parameters.
The container enters a scope before function execution, injects all dependencies, and exits the scope when the function returns.

!!! note
    The decorator only injects parameters annotated with `Injected[T]` or `Annotated[T, Inject()]`.
    These annotations are equivalent—`Injected[T]` is simply an alias for convenience.

```python
from wireup import Injected

@wireup.inject_from_container(container)
def client_function(
    service: Injected[RandomService], 
    scoped_service: Injected[ScopedService], 
    env_name: Annotated[str, Inject(param="env")]
) -> None: ...
```

### Using an existing scoped container

If you have already created a scoped container elsewhere, provide a callable that returns it as the second argument.
Wireup will use that container instead of creating a new scope:

```python
scoped_container: ContextVar[ScopedSyncContainer] = ContextVar("scoped_container")

@wireup.inject_from_container(container, scoped_container.get)
def client_function(
    service: Injected[RandomService], 
    scoped_service: Injected[ScopedService], 
    env_name: Annotated[str, Inject(param="env")]
) -> None: ...
```

### Creating a decorator alias

For cleaner code, you can alias the decorator:

```python
scoped_container: ContextVar[ScopedSyncContainer] = ContextVar("scoped_container")
injected = wireup.inject_from_container(container, scoped_container.get)

@injected
def client_function(
    service: Injected[RandomService], 
    scoped_service: Injected[ScopedService], 
    env_name: Annotated[str, Inject(param="env")]
) -> None: ...
```


## Additional notes

* Works with both sync and async containers
* For `async def` functions, use an async container created via `wireup.create_async_container`

## API Reference

### `wireup.inject_from_container`

::: wireup._decorators.inject_from_container

