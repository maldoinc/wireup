---
description: Migrate FastAPI Depends to Wireup with a low-risk, step-by-step path, including factory-first migration, lifetimes, and request/background task injection.
---

# Migrate from FastAPI Depends to Wireup

If you're evaluating FastAPI DI options, this guide shows a practical migration path from
`fastapi.Depends` to Wireup without rewriting your app. `Depends` works well for many FastAPI
applications. Wireup is for teams that want startup graph validation, explicit lifetimes, and a shared DI graph across
framework and non-framework runtimes.

The core idea is simple:

- Keep FastAPI for HTTP concerns (`Query`, `Header`, `Path`, auth dependencies, request parsing).
- Keep FastAPI for response modeling and serialization (`response_model`, status codes, response classes).
- Move your service graph (repositories, services, clients, settings, domain context) to Wireup.

!!! info "Need full FastAPI integration setup?"

    This page focuses on migration strategy and mechanical rewrites. For full integration setup, advanced usage, and API
    details, see the [FastAPI integration guide](../integrations/fastapi/index.md).

## Not Leaving the FastAPI Ecosystem

This migration does **not** replace FastAPI. FastAPI stays your web framework, router, validation layer, and OpenAPI
generator. Auth extraction can stay in FastAPI, while auth/domain services can be managed by Wireup.

## Why Use Wireup with FastAPI

- A missing dependency, circular dependency, or wrong dependency scope/shape fails at startup rather than when a route
    is first hit.
- Shared services are defined once and reused across FastAPI, CLI commands, workers, and scripts instead of rebuilding
    DI wiring per runtime.
- Reusable sub-graphs let you run multiple configured instances of the same dependency graph without duplicating wiring.
- `singleton`, `scoped`, and `transient` lifetimes are explicit and enforced, avoiding ad-hoc lifetime workarounds
    (`lru_cache`, `app.state`, custom factories).
- With class-based handlers, constructor dependencies are resolved at startup instead of per request.

## Feature Comparison

| Feature                                                               | Wireup | FastAPI `Depends`   |
| --------------------------------------------------------------------- | ------ | ------------------- |
| Async dependency support                                              | ✅      | ✅                   |
| Built-in service lifetimes (`singleton` / `scoped` / `transient`)     | ✅      | request-scoped only |
| Startup graph validation (missing deps, cycles, lifetime mismatches)  | ✅      | ❌                   |
| Single DI graph shared across web, CLI, workers, and scripts          | ✅      | ❌                   |
| Nested service graphs without route-level dependency chaining         | ✅      | ❌                   |
| Zero per-request DI overhead path (class-based handlers with ctor DI) | ✅      | ❌                   |

## When `Depends` Chains Start Getting Big

This pattern is common and valid but as the graph grows, the amount of explicit dependency wiring also grows:

=== "`Depends` chain example"

    ```python linenums="1"
    class DB: ...


    class UserRepo:
        def __init__(self, db: DB) -> None:
            self.db = db


    class Cache: ...


    class Metrics: ...


    class AuthService:
        def __init__(self, repo: UserRepo, cache: Cache, metrics: Metrics) -> None:
            self.repo = repo
            self.cache = cache
            self.metrics = metrics


    class UserService:
        def __init__(self, auth: AuthService, repo: UserRepo) -> None:
            self.auth = auth
            self.repo = repo


    @lru_cache
    def get_db() -> DB:
        return DB()


    @lru_cache
    def get_repo(db: Annotated[DB, Depends(get_db)]) -> UserRepo:
        return UserRepo(db)


    @lru_cache
    def get_cache() -> Cache:
        return Cache()


    @lru_cache
    def get_metrics() -> Metrics:
        return Metrics()


    @lru_cache
    def get_auth_service(
        repo: Annotated[UserRepo, Depends(get_repo)],
        cache: Annotated[Cache, Depends(get_cache)],
        metrics: Annotated[Metrics, Depends(get_metrics)],
    ) -> AuthService:
        return AuthService(repo=repo, cache=cache, metrics=metrics)


    @lru_cache
    def get_user_service(
        auth: Annotated[AuthService, Depends(get_auth_service)],
        repo: Annotated[UserRepo, Depends(get_repo)],
    ) -> UserService:
        return UserService(auth=auth, repo=repo)


    @app.get("/users/{user_id}")
    async def get_user(
        user_id: str,
        service: Annotated[UserService, Depends(get_user_service)],
    ):
        return await service.get_user(user_id)
    ```

=== "Wireup equivalent"

    This is optional cleanup, not a required rewrite. It replaces function factories with type-annotated class
    injectables. See below for a low-risk port that lets you reuse existing factories if you prefer that style.

    ```python linenums="1"
    @injectable
    class DB: ...


    @injectable
    class UserRepo:
        def __init__(self, db: DB) -> None:
            self.db = db


    @injectable
    class Cache: ...


    @injectable
    class Metrics: ...


    @injectable
    class AuthService:
        def __init__(self, repo: UserRepo, cache: Cache, metrics: Metrics) -> None:
            self.repo = repo
            self.cache = cache
            self.metrics = metrics


    @injectable
    class UserService:
        def __init__(self, auth: AuthService, repo: UserRepo) -> None:
            self.auth = auth
            self.repo = repo


    @app.get("/users/{user_id}")
    async def get_user(
        user_id: str,
        service: Injected[UserService],
    ):
        return await service.get_user(user_id)
    ```
With class-based injectables, this becomes `@injectable` registrations plus `Injected[UserService]` at the route.

## FastAPI `Depends` Caveats

### 1) Type hints do not validate the return type of dependency functions

Results of `Depends` are not statically type-checked, so there is no guarantee that a dependency function returns the expected type.

```python
@app.get("/users")
async def list_users(
    # ❓ No static guarantee that get_user_service returns UserService.
    user_service: Annotated[UserService, Depends(get_user_service)],
    # ❌ Type checker won't spot that get_user_service does not return AuthService.
    auth_service: Annotated[AuthService, Depends(get_user_service)],
): ...
```

This means dependency-function mixups are usually caught in tests or at runtime, not by static typing.

### 2) Singleton helpers are process-global

FastAPI singletons are usually process-global. With `@lru_cache`, state can leak across tests if the
returned object is mutable and the cache is not reset.

### 3) Async singleton resources cannot use `@lru_cache`

`@lru_cache` cannot be used with `async def`, so singleton async clients are usually managed through lifespan +
`app.state`.

=== "FastAPI (`lifespan` + `app.state`)"

    ```python
    from contextlib import asynccontextmanager
    import aiohttp
    from fastapi import FastAPI, Request


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with aiohttp.ClientSession() as client:
            app.state.http_client = client
            yield


    app = FastAPI(lifespan=lifespan)


    async def get_http_client(request: Request) -> aiohttp.ClientSession:
        return request.app.state.http_client
    ```

    This also means nothing that relies on `get_http_client` can be a singleton that is evaluated only once, any dependency
    on it will keep being re-evaluated on a per-request basis only to return the same client instance.

    This is a minimal example. In real apps, you often have multiple async singletons that depend on each other, which
    usually means additional dependency wiring.

=== "Wireup (factory + injection)"

    ```python
    from collections.abc import AsyncIterator
    import aiohttp
    from wireup import Injected, injectable


    @injectable
    async def http_client_factory() -> AsyncIterator[aiohttp.ClientSession]:
        async with aiohttp.ClientSession() as client:
            yield client


    @app.get("/weather")
    async def weather(client: Injected[aiohttp.ClientSession]): ...
    ```

### 4) Larger graphs require more explicit wiring review

As service graphs get larger, teams typically spend more time reviewing dependency factories and wiring paths. Wireup
adds startup graph validation for this layer.

## What Stays in FastAPI vs Moves to Wireup

| Concern                                         | Keep in FastAPI (`Depends`, `Query`, `Header`, etc.) | Move to Wireup                                                                                     |
| ----------------------------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Request parsing and validation                  | Yes                                                  | No                                                                                                 |
| HTTP auth extraction (OAuth2, bearer, API keys) | Yes                                                  | Yes, for request-scoped auth/domain services via `Request`                                         |
| Service/repository/client construction          | No                                                   | Yes                                                                                                |
| App settings and long-lived clients             | No                                                   | Yes                                                                                                |
| Request-scoped domain services/context          | No                                                   | Yes (`lifetime="scoped"`)                                                                          |
| Decorators/middleware needing container access  | Sometimes                                            | Sometimes. See [Request-Time Injection](../integrations/fastapi/request_time_injection.md) |

Keeping this boundary explicit prevents confusion when both systems coexist during migration.

## First Commit: Enable Wireup

Add Wireup to the app first, then migrate one endpoint at a time.

```python title="main.py"
import wireup
import wireup.integration.fastapi
from fastapi import FastAPI
from wireup import Injected, injectable


@injectable
class HealthService:
    def status(self) -> dict:
        return {"ok": True}


container = wireup.create_async_container(
    injectables=[HealthService],
)

app = FastAPI()


@app.get("/health")
async def health(service: Injected[HealthService]):
    return service.status()


# Important: call setup after routes are added.
wireup.integration.fastapi.setup(container, app)
```

For setup details and advanced usage, see the [FastAPI integration guide](../integrations/fastapi/index.md).

## Core Migration Steps (Mechanical Before/After)

The snippets below are migration templates: copy the example, adapt names, and apply incrementally. They focus on DI
shape, not full app bootstrap. For full setup (`create_async_container`, module registration, and
`wireup.integration.fastapi.setup(...)`), see the [FastAPI integration guide](../integrations/fastapi/index.md).

### 1) Service factory chains

This is the core rewrite you'll repeat during migration.
Wireup also supports a factory-first style, so you can keep function factories after migration if that fits
your team conventions. This is also the easiest initial migration path because it reuses most of your existing wiring.

Mapping for the factory-first migration path:

| Current FastAPI usage                  | Wireup mapping                   | Where it applies                          |
| -------------------------------------- | -------------------------------- | ----------------------------------------- |
| `@lru_cache` on dependency function    | `@injectable`                    | Wireup factory functions                  |
| No `@lru_cache` on dependency function | `@injectable(lifetime="scoped")` | Wireup factory functions (request-scoped) |
| `x: Annotated[X, Depends(get_x)]`      | `x: Injected[X]`                 | Route handlers only                       |
| `x: Annotated[X, Depends(get_x)]`      | `x: X`                           | Wireup services or factories              |

=== "1) Current (`Depends`)"

    ```python
    class Repo:
        def __init__(self, db: DB) -> None:
            self.db = db


    class Service:
        def __init__(self, repo: Repo) -> None:
            self.repo = repo


    @lru_cache
    def get_repo(db: Annotated[DB, Depends(get_db)]) -> Repo:
        return Repo(db)


    @lru_cache
    def get_service(repo: Annotated[Repo, Depends(get_repo)]) -> Service:
        return Service(repo)


    @app.get("/items")
    async def list_items(service: Annotated[Service, Depends(get_service)]):
        return service.list()
    ```

=== "2) Low-risk Wireup port (keep factories)"

    ```python
    class Repo:
        def __init__(self, db: DB) -> None:
            self.db = db


    class Service:
        def __init__(self, repo: Repo) -> None:
            self.repo = repo


    @injectable
    def get_repo(db: DB) -> Repo:
        return Repo(db)


    @injectable
    def get_service(repo: Repo) -> Service:
        return Service(repo)


    @app.get("/items")
    async def list_items(service: Injected[Service]):
        return service.list()
    ```

=== "3) Optional cleanup (remove redundant factories)"

    ```python
    @injectable
    class Repo:
        def __init__(self, db: DB) -> None:
            self.db = db


    @injectable
    class Service:
        def __init__(self, repo: Repo) -> None:
            self.repo = repo


    @app.get("/items")
    async def list_items(service: Injected[Service]):
        return service.list()
    ```

### 2) Singleton via `@lru_cache`

`@lru_cache` is a global process cache. If tests mutate the returned object, state can leak between tests unless the
cache is reset. Also, in async routes, sync dependency functions run in a threadpool.

=== "Depends"

    ```python
    from typing import Annotated
    from fastapi import Depends


    class Settings(BaseSettings): ...


    @lru_cache
    def get_settings() -> Settings:
        return Settings()


    @app.get("/config")
    async def read_config(settings: Annotated[Settings, Depends(get_settings)]):
        return {"debug": settings.debug}
    ```

=== "Wireup"

    ```python
    from wireup import Injected, injectable


    @injectable
    class Settings(BaseSettings): ...


    @app.get("/config")
    async def read_config(settings: Injected[Settings]):
        return {"debug": settings.debug}
    ```

### 3) Request-scoped objects

If your scoped service needs `fastapi.Request`, include `wireup.integration.fastapi` in `injectables` during container
creation:

```python
container = wireup.create_async_container(
    injectables=[services, wireup.integration.fastapi],
)
```

=== "Depends"

    ```python
    from typing import Annotated
    from fastapi import Depends, Request


    class RequestContext:
        def __init__(self, request: Request) -> None:
            self.request = request


    async def get_request_ctx(request: Request) -> RequestContext:
        return RequestContext(request)


    @app.get("/whoami")
    async def whoami(ctx: Annotated[RequestContext, Depends(get_request_ctx)]):
        return {"path": ctx.request.url.path}
    ```

=== "Wireup"

    ```python
    import fastapi
    from wireup import Injected, injectable


    @injectable(lifetime="scoped")
    class RequestContext:
        def __init__(self, request: fastapi.Request) -> None:
            self.request = request


    @app.get("/whoami")
    async def whoami(ctx: Injected[RequestContext]):
        return {"path": ctx.request.url.path}
    ```

### 4) Async per-request transaction (`yield` cleanup)

`yield`-based cleanup is fully supported in Wireup.

=== "Depends"

    ```python
    from collections.abc import AsyncIterator
    from typing import Annotated
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_maker = async_sessionmaker(engine, expire_on_commit=False)


    async def get_db_session() -> AsyncIterator[AsyncSession]:
        session = session_maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


    @app.post("/transfer")
    async def transfer_money(
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ):
        # do DB writes...
        return {"ok": True}
    ```

=== "Wireup"

    ```python
    from collections.abc import AsyncIterator
    import wireup
    import wireup.integration.fastapi
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from wireup import Injected, injectable

    session_maker = async_sessionmaker(engine, expire_on_commit=False)


    @injectable(lifetime="scoped")
    async def db_session_factory() -> AsyncIterator[AsyncSession]:
        session = session_maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


    @app.post("/transfer")
    async def transfer_money(session: Injected[AsyncSession]):
        # do DB writes...
        return {"ok": True}
    ```

See [Resource Management](../resources.md) for more lifecycle examples.

### 5) Keep FastAPI-native params, move service wiring

=== "Depends + FastAPI params"

    ```python
    class UserService:
        def from_token(self, token: str | None) -> dict:
            return {"token": token}


    @app.get("/me")
    async def me(
        token: Annotated[str | None, Header()] = None,
        service: Annotated[UserService, Depends(get_user_service)],
    ):
        return service.from_token(token)
    ```

=== "Wireup + FastAPI params"

    ```python
    @injectable
    class UserService:
        def from_token(self, token: str | None) -> dict:
            return {"token": token}


    @app.get("/me")
    async def me(
        token: Annotated[str | None, Header()] = None,
        service: Injected[UserService],
    ):
        return service.from_token(token)
    ```

### 6) Background task callbacks

Use this when task callbacks need DI-managed services.

=== "Depends + explicit service passing"

    ```python
    from typing import Annotated
    from fastapi import BackgroundTasks, Depends


    def write_greeting(name: str, greeter: GreeterService) -> None:
        print(greeter.greet(name))


    @app.post("/enqueue")
    async def enqueue(
        name: str,
        tasks: BackgroundTasks,
        greeter: Annotated[GreeterService, Depends(get_greeter_service)],
    ):
        # Pass resolved dependencies explicitly into the task callback.
        tasks.add_task(write_greeting, name, greeter)
        return {"ok": True}
    ```

=== "Wireup + injected task callback (`WireupTask`)"

    `WireupTask` is a container-aware wrapper that resolves injectable callback parameters when the task executes.

    ```python
    from fastapi import BackgroundTasks
    from wireup import Injected
    from wireup.integration.fastapi import WireupTask


    def write_greeting(name: str, greeter: Injected[GreeterService]) -> None:
        print(greeter.greet(name))


    @app.post("/enqueue")
    async def enqueue(
        name: str,
        tasks: BackgroundTasks,
        wireup_task: Injected[WireupTask],
    ):
        tasks.add_task(wireup_task(write_greeting), name)
        return {"ok": True}
    ```

See [FastAPI background tasks](../integrations/fastapi/background_tasks.md) for `Response(background=...)` examples and
scope behavior details.

### 7) Router-level pre-handler checks (`dependencies=[Depends(...)]`)

Use this when logic must run before the endpoint body. This requires `middleware_mode=True` on FastAPI setup
(not on container creation). The code looks different between the two, but
it is equivalent.

```python
wireup.integration.fastapi.setup(
    container,
    app,
    middleware_mode=True,  # Required for request-time helpers using @inject.
)
```

=== "Depends (router dependency)"

    ```python
    from typing import Annotated, Callable
    from fastapi import APIRouter, Depends, HTTPException


    # Assume AuthService is already defined in your app.
    def get_auth_service() -> AuthService:
        return AuthService()


    def require_permission(permission: str) -> Callable[..., None]:
        async def checker(
            auth: Annotated[AuthService, Depends(get_auth_service)],
        ) -> None:
            if not await auth.has_permission(permission):
                raise HTTPException(status_code=403, detail="Forbidden")

        return checker


    router = APIRouter(
        prefix="/admin",
        dependencies=[Depends(require_permission("users:read"))],
    )


    @router.get("/users")
    async def list_users(
        service: Annotated[UserService, Depends(get_user_service)],
    ):
        return await service.list_all()
    ```

=== "Wireup (generator-style route decorator)"

    `@inject` enables Wireup injection in non-route callables (for example, decorators and helpers). Route handlers do
    not need it.

    ```python
    import contextlib
    from collections.abc import AsyncIterator
    from fastapi import APIRouter, HTTPException
    from wireup import Injected
    from wireup.integration.fastapi import inject

    router = APIRouter(prefix="/admin")


    @contextlib.asynccontextmanager
    @inject
    async def require_auth(auth: Injected[AuthService]) -> AsyncIterator[None]:
        if not await auth.is_authenticated():
            raise HTTPException(status_code=401, detail="Authentication required")

        yield


    @router.get("/users")
    @require_auth()
    async def list_users(service: Injected[UserService]):
        return await service.list_all()
    ```

## Testing

=== "Before (`Depends` + `app.dependency_overrides`)"

    ```python
    from fastapi import FastAPI
    from fastapi.testclient import TestClient


    def test_get_user(app: FastAPI):
        app.dependency_overrides[get_user_service] = lambda: FakeUserService()
        try:
            with TestClient(app) as client:
                response = client.get("/users/123")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
    ```

=== "After (Wireup override context manager)"

    ```python
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from wireup.integration.fastapi import get_app_container


    def test_get_user(app: FastAPI):
        with get_app_container(app).override.injectable(
            UserService, new=FakeUserService()
        ):
            with TestClient(app) as client:
                response = client.get("/users/123")

        assert response.status_code == 200
    ```

## Incremental Migration Plan

1. Integrate Wireup once. Create container and call `wireup.integration.fastapi.setup(container, app)` after routes are
    registered.
1. Migrate leaf services (services that don't depend on other services you've written). Add `@injectable` to them, then
    migrate their immediate consumers.
1. Migrate route parameters by feature. Replace service `Depends(...)` parameters with `Injected[T]`, route-by-route.
1. Keep non-service concerns in FastAPI. Continue using `Query`, `Header`, security dependencies, and request parsing in
    FastAPI.
1. Adopt lifetimes intentionally. Make shared clients/settings `singleton`, request context/auth/session `scoped`, and
    short-lived values `transient`.

### Leaf node migration example

This is usually your first safe move: migrate a service with no internal service dependencies.

=== "Before (Depends)"

    ```python
    from pydantic_settings import BaseSettings


    class Settings(BaseSettings):
        timeout_seconds: int = 5


    def get_settings() -> Settings:
        return Settings()


    @app.get("/healthz")
    async def healthz(settings: Annotated[Settings, Depends(get_settings)]):
        return {"timeout_seconds": settings.timeout_seconds}
    ```

=== "After (Wireup leaf node)"

    ```python
    from pydantic_settings import BaseSettings
    from wireup import Injected, injectable


    @injectable
    class Settings(BaseSettings):
        timeout_seconds: int = 5


    @app.get("/healthz")
    async def healthz(settings: Injected[Settings]):
        return {"timeout_seconds": settings.timeout_seconds}
    ```

No repository/service chain changes are needed yet. You can migrate one leaf service at a time, then move to services
that depend on those leaves.

## Common Pitfalls

- Mixing systems without a boundary creates unclear ownership. Example: one module builds services via `Depends`,
    another via Wireup for the same domain service. Pick one owner per service graph area.
- Calling `setup(...)` before all routers are registered can lead to missing wiring. Avoid this by calling
    `wireup.integration.fastapi.setup(container, app)` after routes/routers are added.
- Making Wireup services depend on FastAPI `Depends` outputs is not supported. Keep request parsing/security extraction
    in FastAPI, then pass results to Wireup-managed services at the boundary.

## Next Steps

- [Full FastAPI Integration Guide](../integrations/fastapi/index.md)
- [FastAPI Request-Time Injection](../integrations/fastapi/request_time_injection.md)
