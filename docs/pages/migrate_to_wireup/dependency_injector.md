---
description: Migrate from dependency-injector to Wireup with practical provider-to-injectable mappings, async resource patterns, lifetime rules, and incremental migration guide.
---

# Migrate from Dependency Injector to Wireup

If you're looking for a Dependency Injector alternative with a type-first API, this guide shows how to migrate from
`dependency-injector` to Wireup with practical before/after patterns.
If you've hit friction around async resource patterns or want more startup-time validation of DI misconfigurations, this
guide is designed for that migration path.

The core idea is simple:

- Keep your existing framework (FastAPI, CLI tools, workers, scripts).
- Move from provider-object wiring to type-based injectables.

This migration is mostly a shift from provider objects to type-based injectables, not a rewrite of your application
architecture.

!!! info "Framework examples are illustrative"

    This page uses FastAPI examples frequently because they make DI wiring differences easy to see in small snippets.
    The migration patterns apply beyond FastAPI. Wireup also supports Flask, Django, Starlette, AIOHTTP, Click, Typer,
    and Strawberry integrations.

In the service layer, the biggest shift is structure. Wireup does not rely on one central container class where all
providers are declared. Instead, you annotate services and factories in place with `@injectable` and `Inject(...)`, and
Wireup builds the graph from those declarations. Compared with Dependency Injector's provider-first style, this is a
more decentralized model.

Another shift is how provider types are expressed. In Dependency Injector, different behaviors are modeled with
different provider classes (`Singleton`, `Factory`, `Resource`, and so on). In Wireup, the same `@injectable` model is
used with lifetime configuration and `yield`-based factories for resources. This gives a more unified API, and because
dependency shapes come from function/class signatures, they evolve with the code instead of being split across separate
provider declarations.

## Why Migrate to Wireup

### 1) Limited async capabilities in Dependency Injector

Dependency Injector does not have a first-class provider for a per-request async generator with teardown. In practice,
this means DB transactions or other per-request resources that need async context-managed creation must delegate this responsibility to other systems.

With Wireup:

```python
import contextlib
from collections.abc import AsyncIterator
from wireup import Injected, injectable


class ScopedDbSession:
    async def aclose(self) -> None: ...


@injectable(lifetime="scoped")
async def db_session_factory() -> AsyncIterator[ScopedDbSession]:
    async with contextlib.aclosing(ScopedDbSession()) as sess:
        yield sess


@app.post("/transfer")
async def transfer_money(session: Injected[ScopedDbSession]): ...
```

In Wireup, the cleanup behavior is defined once in the `@injectable` factory via `yield`, and the scope lifecycle
guarantees teardown at scope exit without extra call-site wrappers.

??? note "Closest match to Wireup's scoped async dependencies"

    ```python
    from typing import Annotated
    from collections.abc import AsyncIterator
    from dependency_injector import containers, providers
    from dependency_injector.wiring import Provide, inject
    from fastapi import Depends, Request


    class ScopedDbSession:
        async def aclose(self) -> None: ...


    class Container(containers.DeclarativeContainer):
        db_session_factory = providers.Factory(ScopedDbSession)


    @inject
    async def get_request_db_session(
        request: Request,
        make_session: Annotated[
            providers.Factory[ScopedDbSession],
            Depends(Provide[Container.db_session_factory.provider]),
        ],
    ) -> AsyncIterator[ScopedDbSession]:
        session = getattr(request.state, "db_session", None)
        if session is None:
            session = make_session()
            request.state.db_session = session
        try:
            yield session
        finally:
            if getattr(request.state, "db_session", None) is session:
                await session.aclose()
                del request.state.db_session


    @app.post("/transfer")
    async def transfer_money(
        session: Annotated[ScopedDbSession, Depends(get_request_db_session)],
    ): ...
    ```

    *If you know a canonical way to achieve this with Dependency Injector alone, please open an issue to correct this
    section.*

### 2) Dependency Injector caveat (`Provide[...]` mapping is runtime wiring)

In Dependency Injector, `Provide[...]` is runtime wiring, and type checkers cannot verify that the mapped provider
actually returns the annotated type.

Dependency Injector + FastAPI example:

```python
from typing import Annotated
from dependency_injector.wiring import Provide
from fastapi import Depends


@app.get("/users")
async def list_users(
    # ❓ No static guarantee this provider resolves UserService
    user_service: Annotated[
        UserService,
        Depends(Provide[Container.user_service]),
    ],
    # ❌ Wiring mistake, provider does not match annotation
    auth_service: Annotated[
        AuthService,
        Depends(Provide[Container.user_service]),
    ],
): ...
```

Non-FastAPI example:

```python
from typing import Annotated
from dependency_injector.wiring import Provide, inject


@inject
def run_job(
    # ❌ Wiring mistake: provider does not match annotation
    auth_service: Annotated[AuthService, Provide[Container.user_service]],
) -> None: ...
```

These mismatches are usually caught by tests or at runtime, not by static typing. In contrast, with Wireup the
dependency key is the type (`Injected[T]`), so there is no call-site `Provide[...]` mapping to mismatch. If a type
cannot be resolved, container creation fails during startup validation.

```python
from wireup import Injected


@app.get("/users")
async def list_users(
    user_service: Injected[UserService],
    auth_service: Injected[AuthService],
): ...
```

### 3) Ceremony at the call site (`Depends(Closing[Provide[...]])`)

For DI resources injected into FastAPI endpoints, cleanup timing is expressed at each call site:

```python
from typing import Annotated
from dependency_injector.wiring import Closing, Provide
from fastapi import Depends


@app.post("/transfer")
async def transfer_money(
    session: Annotated[
        ScopedDbSession,
        Depends(Closing[Provide[Container.db_session]]),
    ],
): ...
```

This is explicit but ceremony-heavy. If `Closing[...]` is omitted where it is needed, request-boundary cleanup does not
run there.

Wireup usage stays intent-only:

```python
from wireup import Injected


@app.post("/transfer")
async def transfer_money(session: Injected[ScopedDbSession]): ...
```

### 4) Wireup validation checks with no equivalent in Dependency Injector

#### Startup dependency-graph validation

In Dependency Injector:

- No single built-in startup step that validates the full graph in one pass (missing deps, circular refs, scope/lifetime
    rule violations, config key issues).

Wireup behavior:

```python
class UnknownDep: ...


@injectable
class Service:
    def __init__(self, missing: UnknownDep) -> None:
        self.missing = missing


# Fails immediately during container creation.
container = wireup.create_sync_container(injectables=[Service])
```

Dependency Injector behavior (not caught at container creation):

```python
from dependency_injector import containers, providers


class MissingDep: ...


class Service:
    def __init__(self, missing: MissingDep) -> None:
        self.missing = missing


class Container(containers.DeclarativeContainer):
    service = providers.Singleton(Service)  # missing arg is not validated here


container = (
    Container()
)  # ❌ silently succeeds - misconfiguration not caught here
container.service()  # ❌ fails only when resolved/called
```

#### Enforced lifetime dependency rules

In Dependency Injector:

- No direct equivalent to Wireup's global lifetime-rule validation step.

Wireup behavior:

```python
@injectable(lifetime="scoped")
class RequestCtx: ...


@injectable
class SingletonService:
    # Invalid: singleton depending on scoped dependency.
    def __init__(self, ctx: RequestCtx) -> None:
        self.ctx = ctx


# Fails during validation.
container = wireup.create_sync_container(
    injectables=[RequestCtx, SingletonService]
)
```

Dependency Injector behavior (easy to define, not globally validated at startup):

```python
from dependency_injector import containers, providers


class RequestCtx:
    def __init__(self, request_id: str) -> None:
        self.request_id = request_id


class SingletonService:
    def __init__(self, ctx: RequestCtx) -> None:
        self.ctx = ctx


class Container(containers.DeclarativeContainer):
    request_ctx = providers.ContextLocalSingleton(
        RequestCtx, request_id="req-1"
    )
    singleton_service = providers.Singleton(SingletonService, ctx=request_ctx)


container = Container()  # ❌ no startup validation error
```

## Migrating Provider Types to Injectables

High-level overview of how common Dependency Injector provider types map to Wireup injectables:

| Dependency Injector                    | Wireup                                                                 |
| -------------------------------------- | ---------------------------------------------------------------------- |
| `providers.Singleton(...)`             | `@injectable` class/function (singleton by default)                    |
| `providers.ContextLocalSingleton(...)` | `@injectable(lifetime="scoped")`                                       |
| `providers.Factory(...)`               | `@injectable(lifetime="transient")`                                    |
| `providers.Resource(...)`              | `@injectable` generator/async generator factory                        |
| `providers.Configuration()`            | `Inject(config="...")`                                                 |
| `Provide[...]` + `@inject` wiring      | `Injected[T]` (framework integrations) or `inject_from_container(...)` |

## Container Management in FastAPI

=== "Dependency Injector"

    ```python
    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager
    from dependency_injector import containers, providers
    from fastapi import FastAPI


    class Container(containers.DeclarativeContainer):
        config = providers.Configuration()
        http_client = providers.Resource(...)


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = Container()
        container.config.api_base.from_env("API_BASE")
        container.wire(modules=[__name__])
        await container.init_resources()
        app.container = container
        try:
            yield
        finally:
            await container.shutdown_resources()
            container.unwire()


    app = FastAPI(lifespan=lifespan)
    ```

=== "Wireup"

    ```python
    import wireup
    import wireup.integration.fastapi
    from fastapi import FastAPI

    container = wireup.create_async_container(
        # Let Wireup discover injectables in these modules or list them explicitly.
        injectables=[services, wireup.integration.fastapi],
        config={"api_base": "..."},
    )

    app = FastAPI()
    wireup.integration.fastapi.setup(container, app)
    ```

## Resource Type Migration (Before/After)

### 1) Singleton Service

Type: One shared instance for the entire application/container lifetime.

=== "Dependency Injector"

    ```python
    from typing import Annotated
    from dependency_injector import containers, providers
    from dependency_injector.wiring import Provide, inject
    from fastapi import Depends


    class Settings:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key


    class Container(containers.DeclarativeContainer):
        config = providers.Configuration()
        settings = providers.Singleton(Settings, api_key=config.api_key)


    @app.get("/settings")
    @inject
    async def read_settings(
        settings: Annotated[Settings, Depends(Provide[Container.settings])],
    ):
        return {"api_key": settings.api_key}
    ```

=== "Wireup"

    ```python
    from typing import Annotated
    from wireup import Inject, Injected, injectable


    @injectable
    class Settings:
        def __init__(
            self, api_key: Annotated[str, Inject(config="api_key")]
        ) -> None:
            self.api_key = api_key


    @app.get("/settings")
    async def read_settings(settings: Injected[Settings]):
        return {"api_key": settings.api_key}
    ```

### 2) Transient value (`Factory` -> `transient`)

Type: New instance every time the dependency is resolved.

=== "Dependency Injector"

    ```python
    from typing import Annotated
    from dependency_injector import containers, providers
    from dependency_injector.wiring import Provide, inject
    from fastapi import Depends


    class TokenBuilder:
        def build(self) -> str:
            return "..."


    class Container(containers.DeclarativeContainer):
        token_builder = providers.Factory(TokenBuilder)


    @app.get("/token")
    @inject
    async def token(
        builder: Annotated[TokenBuilder, Depends(Provide[Container.token_builder])],
    ):
        return {"token": builder.build()}
    ```

=== "Wireup"

    ```python
    from wireup import Injected, injectable


    @injectable(lifetime="transient")
    class TokenBuilder:
        def build(self) -> str:
            return "..."


    @app.get("/token")
    async def token(builder: Injected[TokenBuilder]):
        return {"token": builder.build()}
    ```

### 3) Per-request value (`ContextLocalSingleton` -> `scoped`)

Type: One instance per request/task scope, reused within that same scope.

=== "Dependency Injector"

    ```python
    from uuid import uuid4
    from typing import Annotated
    from dependency_injector import containers, providers
    from dependency_injector.wiring import Provide, inject
    from fastapi import Depends


    class RequestId:
        def __init__(self) -> None:
            self.value = uuid4().hex


    class Container(containers.DeclarativeContainer):
        request_id = providers.ContextLocalSingleton(RequestId)


    @app.get("/trace")
    @inject
    async def trace(
        rid: Annotated[RequestId, Depends(Provide[Container.request_id])],
    ):
        return {"request_id": rid.value}
    ```

=== "Wireup"

    ```python
    from uuid import uuid4
    from wireup import Injected, injectable


    @injectable(lifetime="scoped")
    class RequestId:
        def __init__(self) -> None:
            self.value = uuid4().hex


    @app.get("/trace")
    async def trace(rid: Injected[RequestId]):
        return {"request_id": rid.value}
    ```

### 4) Sync Resource with Cleanup

Type: Resource with setup/teardown managed via `yield` (synchronous cleanup).

=== "Dependency Injector"

    ```python
    from typing import Annotated
    import contextlib
    from collections.abc import Iterator
    from dependency_injector import containers, providers
    from dependency_injector.wiring import Provide, inject
    from fastapi import Depends


    class Session:
        def close(self) -> None: ...


    def open_db_session() -> Iterator[Session]:
        with contextlib.closing(Session()) as sess:
            yield sess


    class Container(containers.DeclarativeContainer):
        db_session = providers.Resource(open_db_session)


    @app.get("/users")
    @inject
    async def list_users(
        session: Annotated[Session, Depends(Provide[Container.db_session])],
    ): ...
    ```

=== "Wireup"

    ```python
    import contextlib
    from collections.abc import Iterator
    from wireup import Injected, injectable


    class Session:
        def close(self) -> None: ...


    @injectable(lifetime="scoped")
    def db_session_factory() -> Iterator[Session]:
        with contextlib.closing(Session()) as sess:
            yield sess


    @app.get("/users")
    async def list_users(session: Injected[Session]): ...
    ```

### 5) Async Resource (Function/request scope)

Type: Async resource with setup/teardown managed via `yield`, created per resolution (not shared).

=== "Dependency Injector"

    ```python
    from typing import Annotated
    import contextlib
    from collections.abc import AsyncIterator
    from dependency_injector import containers, providers
    from dependency_injector.wiring import Closing, Provide, inject
    from fastapi import Depends


    class DbSession:
        async def aclose(self) -> None: ...


    async def db_session_resource() -> AsyncIterator[DbSession]:
        async with contextlib.aclosing(DbSession()) as sess:
            yield sess


    class Container(containers.DeclarativeContainer):
        db_session = providers.Resource(db_session_resource)


    @app.post("/transfer")
    @inject
    async def transfer_money(
        session: Annotated[
            DbSession,
            Depends(Closing[Provide[Container.db_session]]),
        ],
    ): ...
    ```

=== "Wireup"

    ```python
    import contextlib
    from collections.abc import AsyncIterator
    from wireup import Injected, injectable


    class DbSession:
        async def aclose(self) -> None: ...


    @injectable(lifetime="transient")
    async def db_session_factory() -> AsyncIterator[DbSession]:
        async with contextlib.aclosing(DbSession()) as sess:
            yield sess


    @app.post("/transfer")
    async def transfer_money(session: Injected[DbSession]): ...
    ```

In Wireup this uses `transient` to represent non-shared resource resolution. For per-request/task cached semantics, use
`scoped` (next section).

### 6) Scoped Async Resource (FastAPI request dependency + DI factory)

Type: Per-request scoped async resource reused inside the same request and closed at request end.

Dependency Injector has no native provider for per-request async resources with teardown. `Resource` is
app-lifecycle-oriented, `Factory` has no async teardown hook, and composing them does not produce reliable per-request
scoping. The only workaround escapes DI and manually manages state in FastAPI dependencies.

??? note "Closest match to Wireup's scoped async dependencies"

    ```python
    from typing import Annotated
    from collections.abc import AsyncIterator
    from dependency_injector import containers, providers
    from dependency_injector.wiring import Provide, inject
    from fastapi import Depends, Request


    class ScopedDbSession:
        async def aclose(self) -> None: ...


    class Container(containers.DeclarativeContainer):
        db_session_factory = providers.Factory(ScopedDbSession)


    @inject
    async def get_request_db_session(
        request: Request,
        make_session: Annotated[
            providers.Factory[ScopedDbSession],
            Depends(Provide[Container.db_session_factory.provider]),
        ],
    ) -> AsyncIterator[ScopedDbSession]:
        session = getattr(request.state, "db_session", None)
        if session is None:
            session = make_session()
            request.state.db_session = session
        try:
            yield session
        finally:
            if getattr(request.state, "db_session", None) is session:
                await session.aclose()
                del request.state.db_session


    @app.post("/transfer")
    async def transfer_money(
        session: Annotated[ScopedDbSession, Depends(get_request_db_session)],
    ): ...
    ```

    *If you know a canonical way to achieve this with Dependency Injector alone, please open an issue to correct this
    section.*

Wireup:

```python
import contextlib
from collections.abc import AsyncIterator
from wireup import Injected, injectable


class ScopedDbSession:
    async def aclose(self) -> None: ...


@injectable(lifetime="scoped")
async def db_session_factory() -> AsyncIterator[ScopedDbSession]:
    async with contextlib.aclosing(ScopedDbSession()) as sess:
        yield sess


@app.post("/transfer")
async def transfer_money(session: Injected[ScopedDbSession]): ...
```

Dependency Injector cannot express this pattern purely within its provider system. In practice, this requires delegating
lifecycle management to FastAPI. Wireup handles it with `@injectable(lifetime="scoped")` on an async generator.

### 7) Configuration Values

Type: Inject runtime configuration values into services without manual wiring.

=== "Dependency Injector"

    ```python
    from typing import Annotated
    from dependency_injector.wiring import Provide, inject
    from fastapi import Depends

    from dependency_injector import containers, providers


    class WeatherService:
        def __init__(self, api_key: str, timeout_seconds: int) -> None:
            self.api_key = api_key
            self.timeout_seconds = timeout_seconds


    class Container(containers.DeclarativeContainer):
        config = providers.Configuration()
        weather = providers.Factory(
            WeatherService,
            api_key=config.weather_api_key,
            timeout_seconds=config.timeout.as_int(),
        )


    @app.get("/forecast")
    @inject
    async def forecast(
        service: Annotated[WeatherService, Depends(Provide[Container.weather])],
    ): ...
    ```

=== "Wireup"

    ```python
    from typing import Annotated
    from wireup import Inject, Injected, injectable


    @injectable
    class WeatherService:
        def __init__(
            self,
            api_key: Annotated[str, Inject(config="weather_api_key")],
            timeout_seconds: Annotated[int, Inject(config="timeout")],
        ) -> None:
            self.api_key = api_key
            self.timeout_seconds = timeout_seconds


    @app.get("/forecast")
    async def forecast(service: Injected[WeatherService]): ...
    ```

Wireup config values are passed explicitly when creating the container:

```python
import os
import wireup

container = wireup.create_async_container(
    injectables=[WeatherService],
    config={
        "weather_api_key": os.environ["WEATHER_API_KEY"],
        "timeout": int(os.environ.get("WEATHER_TIMEOUT", "5")),
    },
)
```

## Injection Outside FastAPI

When an integration exists (FastAPI, Flask, Django, Starlette, AIOHTTP, Click, Typer), prefer that integration's
automatic injection model first. Use `@inject_from_container` as an advanced pattern for scripts, jobs, custom runtime
hooks, or frameworks without a dedicated Wireup integration.

=== "Dependency Injector"

    ```python
    from typing import Annotated
    from dependency_injector.wiring import Provide, inject


    @inject
    def run_job(
        service: Annotated[UserService, Provide[Container.user_service]],
    ) -> None:
        service.run()
    ```

=== "Wireup"

    ```python
    from wireup import Injected, inject_from_container


    @inject_from_container(container)
    def run_job(service: Injected[UserService]) -> None:
        service.run()
    ```

## Testing and Overrides

Both libraries support context-manager based overrides in tests.

=== "Dependency Injector"

    ```python
    from unittest.mock import MagicMock

    service_mock = MagicMock(spec=UserService)

    with container.user_service.override(service_mock):
        assert container.user_service() is service_mock
    ```

=== "Wireup"

    ```python
    from unittest.mock import MagicMock

    service_mock = MagicMock(spec=UserService)

    with container.override.injectable(UserService, new=service_mock):
        assert container.get(UserService) is service_mock
    # UserService is back to normal after the block.
    ```

## Suggested Migration Order

1. Keep your framework/runtime setup; migrate one provider group at a time.
1. Start with singleton/factory providers that have no complex cleanup.
1. Migrate resource providers (`providers.Resource`) to generator factories.
1. Move FastAPI route signatures from `Provide[...]`/`Depends(...)` to `Injected[T]`.
1. Remove old container wiring after all consumers are migrated.
