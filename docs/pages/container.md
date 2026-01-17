The container is the central registry for all application dependencies. It manages the lifecycle of injectables, resolves dependencies, and holds configuration.

## Creation

Wireup provides two ways to create containers, depending on whether your application is synchronous or asynchronous.

### `create_sync_container`

Use this for traditional, blocking Python applications (e.g., Flask, Django, scripts).

```python
container = wireup.create_sync_container(
    injectables=[...],
    config={...}
)
```

### `create_async_container`

Use this for `async/await` based applications (e.g., FastAPI, Starlette). It supports `async` factories and has `async` methods for retrieval and cleanup.

```python
container = wireup.create_async_container(
    injectables=[...],
    config={...}
)
```

### Arguments

Both creation functions accept the following arguments:

| Argument | Type | Description |
| :--- | :--- | :--- |
| `injectables` | `list[ModuleType | type | Callable]` | A list of modules to scan for `@injectable` decorated classes, or direct references to the classes/functions themselves. |
| `config` | `dict[str, Any]` | A detailed configuration dictionary. Values from this dictionary can be injected using `Inject(config="key")`. |




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

**Qualifiers**: Use the `qualifier` argument to retrieve specific implementations when multiple are registered. See [Interfaces](interfaces.md) for more details.

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

Create a scoped container for request-scoped or unit-of-work lifetimes.

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

### `override`

Substitute dependencies for testing. Access via `container.override`.

```python
with container.override.injectable(target=Database, new=mock_db):
    ...  # All injections of Database use mock_db
```

See [Testing](testing.md) for details.


## Eager Initialization

By default, objects are created lazily when first requested. 
To avoid latency on first request for expensive services, initialize them at startup:

```python
for dependency in [HeavyComputeService, MLModelService, Database]:
    container.get(dependency)  # or `await container.get(dependency)` for async
```

## Next Steps

* [Lifetimes & Scopes](lifetimes_and_scopes.md) - Control singleton, scoped, and transient lifetimes.
* [Factories](factories.md) - Create complex injectables and third-party objects.
* [Testing](testing.md) - Override dependencies and test with the container.

