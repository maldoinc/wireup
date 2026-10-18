This page explains what Wireup validates and when those checks happen.

The summary is:

- Wireup validates the registration graph when the container is created.
- Wireup also validates injection targets it can inspect up front, such as `@inject_from_container(...)` functions.
- Wireup offers the same validation for integrations that it can inspect up front. Look on the integration's documentation for details on whether it does upfront validation.
- Dependency requests that are only decided later by your code can still fail when they happen.
- Wireup does not validate the runtime behavior inside your constructors and factories.

## What "If The Container Starts, It Works" Means

When container creation succeeds, Wireup has already verified the following:

- Every required dependency is resolvable
- Config keys requested through `Inject(config=...)` exist
- There are no circular dependencies
- There are no duplicate registrations for the same type and qualifier
- Singleton services do not depend on scoped or transient services
- Factories are properly annotated with return types
- `@inject_from_container(...)` functions are checked at module import time. 

Runtime `@inject` usage in some integrations, or arbitrary
`container.get(...)` calls made by your own code cannot be inspected ahead of time.

## Checked When The Container Is Created

These errors fail fast during container creation.

### Duplicate Registration

Wireup rejects two registrations for the same type and qualifier if they come from different sources.

```python
import wireup
from wireup import injectable


@injectable
class Foo: ...


@injectable
def make_foo() -> Foo:
    return Foo()


wireup.create_sync_container(injectables=[Foo, make_foo])
```

Why it fails:

- Wireup found two different ways to build `Foo`

Why this is bad:

- `Foo` is provided by multiple registrations and wireup would have to arbitrarily pick one.
- Small registration or import changes could make your app start using a different implementation without you noticing

### Missing Dependency

If a required dependency is not registered, Wireup fails as soon as it can inspect that injection path.

=== "Container Creation"

    ```python
    import wireup
    from wireup import injectable


    class Database: ...


    @injectable
    class UserRepository:
        def __init__(self, db: Database) -> None:
            self.db = db


    wireup.create_sync_container(injectables=[UserRepository])
    ```

=== "`@inject_from_container(...)`"

    ```python
    import wireup
    from wireup import Injected, inject_from_container


    class UserRepository: ...


    container = wireup.create_sync_container(injectables=[])


    @inject_from_container(container)
    def run_job(repo: Injected[UserRepository]) -> None:
        pass
    ```

=== "FastAPI Setup"

    ```python
    import fastapi
    import wireup
    import wireup.integration.fastapi
    from wireup import Injected


    class UserRepository: ...


    app = fastapi.FastAPI()


    @app.get("/users")
    def get_users(repo: Injected[UserRepository]) -> list[str]:
        return []


    container = wireup.create_sync_container(injectables=[])
    wireup.integration.fastapi.setup(container, app)
    ```

Why it fails:

- Each example asks Wireup for `UserRepository`, but nothing in the container knows how to create it

Why this is bad:

- The function or service cannot run because one of its required inputs is missing

### Missing Config Key

Wireup validates config keys requested through `Inject(config=...)`. Only the presence of the key is checked, not the
value itself.

```python
from typing import Annotated

import wireup
from wireup import Inject, injectable


@injectable
class Database:
    def __init__(self, dsn: Annotated[str, Inject(config="db_url")]) -> None:
        self.dsn = dsn


wireup.create_sync_container(
    injectables=[Database],
    config={},
)
```

Why it fails:

- `Database` asks for `db_url`, but that key is missing from the config you passed to the container

Why this is bad:

- The dependency is missing, and `Database` cannot be created without that setting

### Circular Dependency

Wireup detects dependency cycles in the registration graph.

```python
import wireup
from wireup import injectable


@injectable
class Foo:
    def __init__(self, bar: "Bar") -> None:
        self.bar = bar


@injectable
class Bar:
    def __init__(self, foo: Foo) -> None:
        self.foo = foo


wireup.create_sync_container(injectables=[Foo, Bar])
```

Why it fails:

- To build `Foo`, Wireup needs `Bar`, and to build `Bar`, it needs `Foo`

Why this is bad:

- The dependency graph has no valid starting point, so Wireup cannot build neither `Foo` nor `Bar`
- Your app would get stuck trying to build services that depend on each other in a loop

### Invalid Lifetime Dependency

A singleton cannot depend on a scoped or transient dependency.

```python
import wireup
from wireup import injectable


@injectable(lifetime="scoped")
class RequestContext: ...


@injectable(lifetime="singleton")
class AuditService:
    def __init__(self, ctx: RequestContext) -> None:
        self.ctx = ctx


wireup.create_sync_container(injectables=[RequestContext, AuditService])
```

Why it fails:

- `AuditService` would keep a `RequestContext` that is only meant to live for one request

Why this is bad:

- Later requests could end up using old request data by mistake
- The object would outlive the thing it depends on, which usually leads to stale state and hard-to-track bugs

### Factory Without A Return Type

Wireup uses the return type to determine which service the factory provides.

```python
import wireup
from wireup import injectable


@injectable
def make_foo():
    return Foo()


wireup.create_sync_container(injectables=[make_foo])
```

Why it fails:

- Wireup can see the factory, but it cannot tell what service that function is supposed to provide

Why this is bad:

- There is no clear type to register this factory under
- Different readers and tools would have to guess what `make_foo` is meant to produce

### Missing Type Annotations

Wireup requires type annotations to determine what to inject.

```python
import wireup
from wireup import injectable


@injectable
class UserRepository:
    def __init__(self, db) -> None:
        self.db = db


wireup.create_sync_container(injectables=[UserRepository])
```

Why it fails:

- The `db` parameter has no type annotation, so Wireup does not know what to look up and inject

Why this is bad:

- Wireup would have to guess what `db` means

### Positional-Only Parameters

Wireup injects by keyword argument, so positional-only parameters are rejected.

```python
import wireup
from wireup import injectable


class Database: ...


@injectable
def make_repo(db: Database, /) -> UserRepository:
    return UserRepository(db=db)


wireup.create_sync_container(injectables=[make_repo])
```

Why it fails:

- `db` can only be passed by position, but Wireup injects dependencies by parameter name

Why this is bad:

- Wireup cannot provide dependencies to that function

### Invalid `as_type`

If you register an implementation as another type, the registration has to make sense.

```python
import wireup
from wireup import injectable


class Cache: ...


@injectable(as_type=Cache)
class Mailer: ...


wireup.create_sync_container(injectables=[Mailer])
```

Why it fails:

- The registration says `Mailer` should be used wherever `Cache` is requested, but `Mailer` does not actually implement `Cache`

Why this is bad:

- Code that expects a `Cache` could receive an object with the wrong behavior
- The registration would make the type hints say one thing while the runtime object does another

## Requests Made Later By Your Code

Some errors only happen when your code makes a dependency request Wireup could not have predicted during container
creation or integration setup.

Examples:

- Calling `container.get(Foo)` when `Foo` was never registered
- Calling `container.get(Cache, qualifier="analytics")` when that qualifier does not exist
- Asking a sync container to create an async-only dependency

These are not graph-validation failures. They depend on what your runtime code asks the container to do.

## What Wireup Does Not Validate

Wireup validates the dependency graph. Runtime behavior inside your constructors and factories is outside Wireup's control.