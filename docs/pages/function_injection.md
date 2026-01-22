The `@inject_from_container` decorator injects dependencies directly into function parameters. Use this when building
your own integration or using Wireup in a framework without built-in support.

## Basic Usage

Decorate any function and annotate the parameters you want injected:

```python
from typing import Annotated
from wireup import Inject, Injected, inject_from_container


@inject_from_container(container)
def process_order(
    order_service: Injected[OrderService],
    db_url: Annotated[str, Inject(config="database_url")],
) -> None:
    order_service.process()
```

The decorator:

1. Creates a new scope before the function runs
1. Injects all annotated parameters from that scope
1. Closes the scope when the function returns (triggering cleanup)

### Async Functions

The decorator works with `async` functions. The container must be created using `wireup.create_async_container`.

```python
@inject_from_container(container)
async def process_data(service: Injected[DataService]):
    await service.process()
```

!!! note "Annotations Required"

    Only parameters annotated with `Injected[T]` or `Annotated[T, Inject(...)]` are injected. Unannotated parameters are
    left alone for the caller to provide.

## Advanced Usage

### Using an Existing Scope

If a scope already exists (e.g., created by middleware), pass a callable that returns it as the second argument. The
decorator will use that scope instead of creating a new one.

```python
from contextvars import ContextVar
from wireup import ScopedSyncContainer, inject_from_container

scoped_container: ContextVar[ScopedSyncContainer] = ContextVar(
    "scoped_container"
)


@inject_from_container(container, scoped_container.get)
def handle_request(service: Injected[RequestService]) -> None: ...
```

### Creating a Decorator Alias

For cleaner code, create an alias:

```python
inject = inject_from_container(container, scoped_container.get)


@inject
def handle_request(service: Injected[RequestService]) -> None: ...
```

!!! tip "Framework Integrations"

    If you're using FastAPI, Flask, Django, or another supported framework, the integration handles this for you. See
    [Integrations](integrations/index.md).

## API Reference

### `wireup.inject_from_container`

::: wireup.inject_from_container
