# The Container

The container is the central registry for all application dependencies. It manages the lifecycle of injectables, resolves dependencies, and holds configuration.

## Creation

Wireup provides two factory functions to create containers, depending on whether your application is synchronous or asynchronous.

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
| `injectables` | `list[ModuleType | type | Callable]` | A list of modules to scan for `@injectable` / `@abstract` decorated classes, or direct references to the classes/functions themselves. |
| `config` | `dict[str, Any]` | A detailed configuration dictionary. Values from this dictionary can be injected using `Inject(config="key")`. |


## Core API

### `get`

Retrieve an instance of a registered injectable.

```python
# Sync
db = container.get(Database)
readonly_db = container.get(Database, qualifier="readonly")

# Async
db = await container.get(Database)
readonly_db = await container.get(Database, qualifier="readonly")
```

**Qualifiers**: Use the `qualifier` argument to retrieve specific implementations when multiple are registered.
See [Multiple Registrations](multiple_registrations.md) and [Interfaces](interfaces.md) for more details.

### `close`

Clean up the container and release resources. This triggers the cleanup phase of any generator-based factories.

```python
# Sync
container.close()

# Async
await container.close()
```

## Next Steps

* [Lifetimes & Scopes](lifetimes_and_scopes.md) - Learn how to control the lifetime of your injectables.
* [Factories](factories.md) - Learn how to create complex injectables and manage resources.
* [Testing](testing.md) - Learn how to test your application with Wireup.
