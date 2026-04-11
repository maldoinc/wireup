The container is the object responsible for creating and managing your application's dependencies. When you request a
dependency, whether via type hints, `container.get()`, or a framework integration, the container builds it and any
dependencies it requires.

In practice, you mainly interact with the container directly during setup. Once configured, dependencies flow
automatically through type hints and decorators.

## Creation

Wireup provides two ways to create containers, depending on whether your application is synchronous or asynchronous.

### `create_sync_container`

Use this for traditional, blocking Python applications (e.g., Flask, Django, scripts).

```python
container = wireup.create_sync_container(injectables=[...], config={...})
```

### `create_async_container`

Use this for `async/await` based applications (e.g., FastAPI, Starlette). It supports `async` factories and has `async`
methods for retrieval and cleanup.

```python
container = wireup.create_async_container(injectables=[...], config={...})
```

### Arguments

Both creation functions accept the following arguments:

| Argument                   | Type                                      | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| :------------------------- | :---------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `injectables`              | `list[Union[type, Callable, ModuleType]]` | Classes, functions decorated with `@injectable`, or modules to scan. Modules are scanned recursively, collecting only items decorated with `@injectable`. |
| `config`                   | `dict[str, Any]`                          | Configuration dictionary. Values from this dictionary can be injected using `Inject(config="key")`.                                                                                                                                                                                                                                                                                                                                                                                                         |
| `concurrent_scoped_access` | `bool`                                    | Set to `True` if you share scopes across multiple threads/tasks. Defaults to `False`. See [Lifetimes & Scopes: Concurrent Access](lifetimes_and_scopes.md#concurrent-scope-access) for details.                                                                                                                                                                                                                                                                                                             |

!!! note "Multiple Containers"

    The `@injectable` decorator only stores metadata, it doesn't register anything globally. Each container you create is
    fully independent with its own state.

## Core API

### `get`

Retrieve an instance of a registered injectable.

=== "Synchronous"

    ```python
    db = container.get(Database)
    readonly_db = container.get(Database, qualifier="readonly")
    ```

=== "Async"

    ```python
    db = await container.get(Database)
    readonly_db = await container.get(Database, qualifier="readonly")
    ```

**Qualifiers**: Use the `qualifier` argument to retrieve specific implementations when multiple are registered. See
[Interfaces](interfaces.md) for more details.

!!! important

    Prefer constructor-based dependency injection over calling `get` directly. Use `get` in advanced
    scenarios like dynamic service lookup or when working with framework integration code.

### `close`

Clean up the container and release resources. This triggers the cleanup phase of any generator-based factories.

=== "Synchronous"

    ```python
    container.close()
    ```

=== "Async"

    ```python
    await container.close()
    ```

### `enter_scope`

Create a scoped container. Scoped containers manage their own scoped and transient dependencies while sharing singletons
with the root container. See [Lifetimes & Scopes](lifetimes_and_scopes.md) for details on how scopes work.

You can optionally pass a positional mapping of pre-created instances to provide at scope entry:

```python
with container.enter_scope({DbSession: existing_session}) as scoped:
    db_session = scoped.get(DbSession)  # Uses provided instance
```

See [Sharing Context Across Scopes](lifetimes_and_scopes.md#sharing-context-across-scopes) for more on this feature.

=== "Synchronous"

    ```python
    with container.enter_scope() as scoped:
        db_session = scoped.get(DbSession)  # Fresh instance per scope
    ```

=== "Async"

    ```python
    async with container.enter_scope() as scoped:
        db_session = await scoped.get(DbSession)  # Fresh instance per scope
    ```

See [Lifetimes & Scopes](lifetimes_and_scopes.md) for details.

### `config`

Access configuration values directly from the container. This provides programmatic access to the configuration
dictionary passed during container creation.

```python
env = container.config.get("app_env")
db_url = container.config.get("database_url")
```

!!! important

    Prefer `Inject(config="key")` in dependency constructors over accessing `container.config` directly.


### `override`

Substitute dependencies for testing. Access via `container.override`.

```python
with container.override.injectable(target=Database, new=mock_db):
    ...  # All injections of Database use mock_db
```

See [Testing](testing.md) for details.


## Injecting The Container

The container can inject itself just like any other dependency. This is an advanced feature for infrastructure code that needs runtime container access. This pattern is generally not recommended for regular injectables when you know the required dependencies ahead of time.

Depend on the root container by type:

- `SyncContainer`, `ScopedSyncContainer` when using a synchronous container created via `wireup.create_sync_container`
- `AsyncContainer`, `ScopedAsyncContainer` when using an asynchronous container created via `wireup.create_async_container`

Typical examples include:

- Selecting a handler or implementation at runtime based on a qualifier or runtime data
- Wrapping background tasks or callbacks so they run with Wireup injection
- Coordinating fan-out work across child scopes while letting services inside each child scope access that child scope
- Loading optional integrations only when a feature is enabled

```python
from wireup import SyncContainer, injectable


@injectable
class BackgroundTaskScheduler:
    def __init__(self, container: SyncContainer) -> None:
        self.container = container
```

If you need the active scope rather than the root container, depend on the scoped container type:

```python
from wireup import ScopedSyncContainer, injectable


@injectable(lifetime="scoped")
class JobDispatcher:
    def __init__(self, scope: ScopedSyncContainer) -> None:
        self.scope = scope
```

For a full example of wrapping callables dynamically, see
[Function Injection: Dynamic Function Injection](function_injection.md#dynamic-function-injection). For examples of
passing selected dependencies into child scopes, see
[Lifetimes & Scopes: Sharing Context Across Scopes](lifetimes_and_scopes.md#sharing-context-across-scopes).


## Eager Initialization

By default, objects are created lazily when first requested. To avoid latency on first request for expensive services,
initialize them at startup:

```python
for dependency in [HeavyComputeService, MLModelService, Database]:
    container.get(dependency)  # or `await container.get(dependency)` for async
```

## Next Steps

- [Lifetimes & Scopes](lifetimes_and_scopes.md) - Control how long objects live.
- [Factories](factories.md) - Create complex dependencies and third-party objects.
- [Testing](testing.md) - Override dependencies and test with the container.
