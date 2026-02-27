# Wireup

Type-driven dependency injection for Python. Wireup is battle-tested in production, thread-safe, no-GIL (PEP 703) ready, and designed to fail fast: **if the container starts, it works**.

<div class="grid cards annotate index-cards" markdown>

- :material-shield-check:{ .lg .middle } __Correct by Default__

    ______________________________________________________________________

    Wireup catches missing dependencies, circular references, lifetime mismatches, duplicate registrations, and missing config keys at startup. Shared dependencies are created in a thread-safe way.

    [:octicons-arrow-right-24: Validation checks](#validation-checks)

- :material-share-variant:{ .lg .middle } __Define Once, Inject Anywhere__

    ______________________________________________________________________

    Reuse the same service layer across APIs, CLIs, workers, and scripts without rewriting your dependency wiring.

    [:octicons-arrow-right-24: Function injection](function_injection.md)

- :material-web:{ .lg .middle } __Framework-Ready__

    ______________________________________________________________________

    Native integrations for FastAPI, Flask, Django, Starlette, AIOHTTP, Click, Typer, and Strawberry.

    [:octicons-arrow-right-24: View integrations](integrations/index.md)

- :material-lightning-bolt:{ .lg .middle } __Startup-Resolved Injection__

    ______________________________________________________________________

    Resolve constructor dependencies at startup in [FastAPI](integrations/fastapi/class_based_handlers.md) and [AIOHTTP](integrations/aiohttp/class_based_handlers.md) class-based handlers, not per request.

    [:octicons-arrow-right-24: FastAPI class-based handlers](integrations/fastapi/class_based_handlers.md)


</div>

## Quick Start

```bash
pip install wireup
```

=== "Async + FastAPI"

    Framework-first setup with request-time injection in endpoints.

    ```python title="main.py"
    import fastapi
    import wireup
    import wireup.integration.fastapi
    from wireup import Injected, injectable


    @injectable
    class Database:
        def query(self, sql: str) -> list[str]: ...


    @injectable
    class UserService:
        def __init__(self, db: Database) -> None:
            self.db = db

        def get_users(self) -> list[str]:
            return self.db.query("SELECT name FROM users")


    app = fastapi.FastAPI()


    @app.get("/users")
    def get_users(service: Injected[UserService]) -> list[str]:
        return service.get_users()


    container = wireup.create_async_container(injectables=[Database, UserService])
    wireup.integration.fastapi.setup(container, app)
    ```

=== "Sync + Scripts"

    Plain Python scripts with function injection and no framework dependency.

    ```python title="script.py"
    import wireup
    from wireup import Injected, inject_from_container, injectable


    @injectable
    class Database:
        def execute(self, sql: str) -> None: ...


    container = wireup.create_sync_container(injectables=[Database])


    @inject_from_container(container)
    def run_migration(db: Injected[Database]) -> None:
        db.execute("ALTER TABLE users ADD COLUMN active BOOLEAN DEFAULT true")


    run_migration()
    ```

=== "Config Injection"

    Inject configuration directly into constructors without writing pass-through factories.

    ```python title="config_example.py"
    from typing import Annotated
    import wireup
    from wireup import Inject, injectable


    @injectable
    class Database:
        def __init__(self, db_url: Annotated[str, Inject(config="db_url")]) -> None:
            self.db_url = db_url

        def execute(self, sql: str) -> None: ...


    container = wireup.create_sync_container(
        injectables=[Database],
        config={"db_url": "postgresql://localhost/app"},
    )

    ```

=== "Clean Architecture"

    Need strict boundaries? Use factories to wire pure domain objects and integrate external libraries like Pydantic.
    See [Factories](factories.md) for the full pattern.

    ```python title="wiring.py"
    import wireup
    from wireup import injectable
    from domain import Database
    from settings import Settings

    @injectable
    def make_settings() -> Settings:
        return Settings()


    @injectable
    def make_database(settings: Settings) -> Database:
        return Database(url=settings.db_url)


    container = wireup.create_sync_container(
        injectables=[make_settings, make_database]
    )
    ```

## Browse by Topic

<div class="grid cards index-cards" markdown>

- :material-rocket-launch:{ .lg .middle } __New to Wireup?__

    Set up your first container, inject dependencies, and run your app.

    [Getting Started](getting_started.md)

- :material-package-variant:{ .lg .middle } __Container Basics__

    Learn registration, retrieval, scopes, and overrides.

    [Container](container.md)

- :material-cube-outline:{ .lg .middle } __Injectables & Config__

    Define classes/functions and inject configuration.

    [Injectables](injectables.md) • [Configuration](configuration.md)

- :material-timer-sand:{ .lg .middle } __Lifetimes & Resources__

    Model singleton/scoped/transient behavior and cleanup timing.

    [Lifetimes & Scopes](lifetimes_and_scopes.md) • [Resource Management](resources.md)

- :material-transit-connection-variant:{ .lg .middle } __Advanced Composition__

    Use factories, interfaces, qualifiers, and reusable sub-graphs.

    [Factories](factories.md) • [Interfaces](interfaces.md)

- :material-test-tube:{ .lg .middle } __Testing & Overrides__

    Replace dependencies safely in tests without rewiring your app.

    [Testing](testing.md)

- :material-web:{ .lg .middle } __Framework Integrations__

    FastAPI, Flask, Django, AIOHTTP, Starlette, Strawberry, Click, and Typer.

    [Integrations](integrations/index.md)

- :material-function-variant:{ .lg .middle } __Function Injection__

    Inject into scripts, jobs, handlers, and framework callbacks.

    [Function Injection](function_injection.md)

</div>

## Core Concepts at a Glance

| Concept       | What it gives you                                      | Deep dive                                     |
| ------------- | ------------------------------------------------------ | --------------------------------------------- |
| Container     | Centralized dependency graph and lifecycle management  | [Container](container.md)                     |
| Injectables   | Type-based dependency wiring for classes and functions | [Injectables](injectables.md)                 |
| Configuration | Config injection with startup validation               | [Configuration](configuration.md)             |
| Lifetimes     | `singleton`, `scoped`, `transient` instance control    | [Lifetimes & Scopes](lifetimes_and_scopes.md) |
| Factories     | Advanced creation patterns for complex dependencies    | [Factories](factories.md)                     |
| Resources     | Initialization and cleanup patterns                    | [Resources](resources.md)                     |
| Overrides     | Swap dependencies for tests and local experimentation  | [Testing](testing.md)                         |

## Validation checks

Wireup validates dependencies and configuration at startup.

=== "Container creation"

    ```python
    @injectable
    class Foo:
        def __init__(self, oops: UnknownDep) -> None: ...


    container = wireup.create_sync_container(injectables=[Foo])
    # ❌ Parameter 'oops' of 'Foo' depends on an unknown injectable 'UnknownDep'.
    ```

=== "Function injection"

    ```python
    container = wireup.create_sync_container(injectables=[])


    @inject_from_container(container)
    def my_function(oops: Injected[UnknownDep]) -> None: ...


    # ❌ Parameter 'oops' of 'my_function' depends on an unknown injectable 'UnknownDep'.
    ```

=== "Configuration"

    ```python
    @injectable
    class Database:
        def __init__(self, url: Annotated[str, Inject(config="db_url")]) -> None: ...


    container = wireup.create_sync_container(injectables=[Database], config={})
    # ❌ Parameter 'url' of Type 'Database' depends on an unknown Wireup config key 'db_url'.
    ```

Additional checks include circular dependencies, lifetime mismatches, and duplicate registrations.
See [Container](container.md), [Configuration](configuration.md), and [Function Injection](function_injection.md) for details.

## Next Steps

1. Read [Getting Started](getting_started.md) for an end-to-end setup.
2. Pick your framework from [Integrations](integrations/index.md).
3. Review [Testing](testing.md) before writing integration tests.
