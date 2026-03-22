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

### Dynamic Function Injection

Sometimes the function you want to inject is only known at runtime, for example when scheduling background work on the
event loop. In these cases, inject the root container into an infrastructure service and use it to wrap the callable
before scheduling it.

**Example: Scheduling Background Tasks**

```python
import asyncio
from functools import lru_cache

from wireup import AsyncContainer, Injected, inject_from_container, injectable
from wireup.ioc.types import AnyCallable


@injectable
class BackgroundTasks:
    def __init__(self, container: AsyncContainer) -> None:
        # Build wrappers for callables using this container instance.
        self._inject = inject_from_container(container)
        # Keep strong references to in-flight tasks until they complete.
        self._tasks: set[asyncio.Task] = set()

    @lru_cache(maxsize=128)
    def _wrap(self, fn: AnyCallable) -> AnyCallable:
        # Reuse wrappers for frequently scheduled functions.
        return self._inject(fn)

    def schedule(self, fn, /, *args, **kwargs) -> asyncio.Task:
        task = asyncio.create_task(self._wrap(fn)(*args, **kwargs))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task


async def send_email(
    user_id: str,
    email_service: Injected[EmailService],
) -> None:
    await email_service.send_welcome_email(user_id)


async def handle_signup(
    user_id: str,
    background_tasks: Injected[BackgroundTasks],
) -> None:
    background_tasks.schedule(send_email, user_id)
```

This avoids storing a global container variable while still letting you inject dependencies into functions that are
created or selected dynamically. See [Container: Injecting The Container](container.md#injecting-the-container).

!!! tip "Good to know"

    In the above example, each scheduled task runs in its own Wireup scope, so scoped dependencies are isolated from the caller and from other
    scheduled tasks.


## API Reference

### `wireup.inject_from_container`

::: wireup.inject_from_container
