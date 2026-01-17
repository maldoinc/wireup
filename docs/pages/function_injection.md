!!! note
    When using the provided integrations, this is automatically handled for you.
    Only use this if you're injecting Wireup dependencies in a framework without an integration.

Instead of manually retrieving services via `container.get` or configuration via `container.config`, you can inject them directly into function parameters using the container as a decorator. Works with both sync and async containers.

This transforms verbose manual dependency retrieval:

```python
def client_function() -> None:
    random = container.get(RandomService)
    env_name = container.config.get("env")

    with container.enter_scope() as scoped_container:
        scoped_service = scoped_container.get(ScopedService)
```

Into clean, declarative dependency injection.

## Using `@wireup.inject_from_container`

Use the `inject_from_container` decorator to automatically inject dependencies into function parameters.
The container enters a scope before function execution, injects all dependencies, and exits the scope when the function returns.

!!! note
    The decorator only injects parameters annotated with `Injected[T]` or `Annotated[T, Inject()]`.
    These annotations are equivalent, `Injected[T]` is simply an alias for convenience.
    
    For details on when annotations are required, see [Dependency Annotations](annotations.md).

```python
from wireup import Injected, inject_from_container

@inject_from_container(container)
def client_function(
    service: Injected[RandomService], 
    scoped_service: Injected[ScopedService], 
    env_name: Annotated[str, Inject(config="env")]
) -> None: ...
```

### Async Functions

The decorator works seamlessly with `async` functions, however the container must be created using `wireup.create_async_container`.

```python
@inject_from_container(container)
async def process_data(data: Injected[DataService]):
    await data.process()
```

### Using an existing scoped container

If you have already created a scoped container elsewhere, provide a callable that returns it as the second argument.
Wireup will use that container instead of creating a new scope:

```python
from contextvars import ContextVar
from wireup import ScopedSyncContainer, inject_from_container

scoped_container: ContextVar[ScopedSyncContainer] = ContextVar("scoped_container")

@inject_from_container(container, scoped_container.get)
def client_function(
    service: Injected[RandomService], 
    scoped_service: Injected[ScopedService], 
    env_name: Annotated[str, Inject(config="env")]
) -> None: ...
```

### Creating a decorator alias

For cleaner code, you can alias the decorator:

```python
from contextvars import ContextVar
from wireup import ScopedSyncContainer

scoped_container: ContextVar[ScopedSyncContainer] = ContextVar("scoped_container")
injected = wireup.inject_from_container(container, scoped_container.get)

@injected
def client_function(
    service: Injected[RandomService], 
    scoped_service: Injected[ScopedService], 
    env_name: Annotated[str, Inject(config="env")]
) -> None: ...
```

## API Reference

### `wireup.inject_from_container`

::: wireup._decorators.inject_from_container

