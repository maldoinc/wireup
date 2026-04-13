import asyncio
import contextlib
import uuid
from threading import Barrier, Thread
from typing import Any, AsyncIterator, Dict, Iterator, Set
from uuid import uuid4

import anyio.to_thread
import pytest
import wireup
import wireup.integration
import wireup.integration.fastapi
from fastapi import BackgroundTasks, FastAPI, Request, WebSocket
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from wireup._annotations import Injected, injectable
from wireup.errors import WireupError
from wireup.integration.fastapi import WireupTask, get_app_container, get_request_container
from wireup.ioc.util import is_wireup_injected

from test.integration.fastapi import cbr, wireup_route
from test.integration.fastapi import services as fastapi_test_services
from test.integration.fastapi.router import get_lucky_number, router
from test.shared import shared_services
from test.shared.shared_services.rand import RandomService


def create_app(*, expose_container_in_middleware: bool) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.include_router(wireup_route.router)

    container = wireup.create_async_container(
        injectables=[fastapi_test_services, shared_services, wireup.integration.fastapi],
        config={"foo": "bar"},
    )
    wireup.integration.fastapi.setup(
        container,
        app,
        class_based_handlers=[cbr.MyClassBasedRoute],
        middleware_mode=expose_container_in_middleware,
    )

    return app


@pytest.fixture(params=[True, False], ids=["middleware_mode=True", "middleware_mode=False"])
def expose_container_in_middleware(request: pytest.FixtureRequest) -> bool:
    return request.param


@pytest.fixture()
def app(*, expose_container_in_middleware: bool) -> FastAPI:
    return create_app(expose_container_in_middleware=expose_container_in_middleware)


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def _get_http_route_call(app: FastAPI, path: str) -> Any:
    for route in app.routes:
        if getattr(route, "path", None) == path and hasattr(route, "dependant") and route.dependant.call:
            return route.dependant.call

    msg = f"No HTTP route found for path {path!r}"
    raise AssertionError(msg)


def _wireup_wrapper_count(fn: Any) -> int:
    count = 0
    while hasattr(fn, "__wrapped__"):
        if is_wireup_injected(fn):
            count += 1
        fn = fn.__wrapped__
    if is_wireup_injected(fn):
        count += 1

    return count


def test_injects_service(client: TestClient):
    get_lucky_number._called = 0  # type: ignore[reportFunctionMemberAccess]
    response = client.get("/lucky-number")
    assert response.status_code == 200
    assert response.json() == {"number": 4, "lucky_number": 42}
    # Raise if this will be invoked more than once
    # That would be the case if wireup also "unwraps" and tries
    # to resolve dependencies it doesn't own.
    assert get_lucky_number._called == 1  # type: ignore[reportFunctionMemberAccess]


@pytest.mark.parametrize("endpoint", ["/scoped", "/scoped-sync", "/scoped/wireup_injected"])
def test_scoped(client: TestClient, endpoint: str):
    response = client.get(endpoint)
    assert response.status_code == 200


def test_override(app: FastAPI, client: TestClient):
    class RealRandom(RandomService):
        def get_random(self) -> int:
            return super().get_random() ** 2

    with get_app_container(app).override.injectable(RandomService, new=RealRandom()):
        response = client.get("/rng")
    assert response.status_code == 200
    assert response.json() == {"number": 16}


def test_does_not_affect_unused_endpoints(client: TestClient):
    response = client.get("/rng/depends")
    assert response.status_code == 200
    assert response.json() == {"number": 4}


def test_injects_parameters(client: TestClient):
    response = client.get("/params")
    assert response.status_code == 200
    assert response.json() == {"foo": "bar", "foo_foo": "bar-bar"}


def test_request_container_in_decorator(client: TestClient, *, expose_container_in_middleware: bool):
    if expose_container_in_middleware:
        response = client.get("/requires-request-id")
        assert response.status_code == 401

        response = client.get("/requires-request-id", headers={"X-Request-Id": "req-1"})
        assert response.json() == {"number": 4}
    else:
        with pytest.raises(WireupError, match="middleware_mode=True"):
            client.get("/requires-request-id")


@pytest.mark.parametrize("endpoint", ["/ws", "/ws/wireup_injected", "/ws_in_service", "/ws/no-websocket-in-signature"])
def test_websocket(client: TestClient, endpoint: str):
    with client.websocket_connect(endpoint) as websocket:
        websocket.send_text("World")
        data = websocket.receive_text()
        assert data == "Hello World"


def test_websocket_identity_matches_wireup_context(client: TestClient) -> None:
    with client.websocket_connect("/ws/identity") as websocket:
        assert websocket.receive_text() == "true"


def test_websocket_get_request_container_is_unavailable_in_fastapi_middleware_mode() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.fastapi])

    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            get_request_container()
        except WireupError:
            await websocket.send_text("wireup-error")
        await websocket.close()

    wireup.integration.fastapi.setup(container, app, middleware_mode=True)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            assert websocket.receive_text() == "wireup-error"


@pytest.mark.parametrize("middleware_mode", [True, False], ids=["middleware_mode=True", "middleware_mode=False"])
def test_websocket_singleton_only_route_get_request_container_unavailable(*, middleware_mode: bool) -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.fastapi])

    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket, _random: Injected[RandomService]) -> None:
        await websocket.accept()
        try:
            get_request_container()
        except WireupError:
            await websocket.send_text("wireup-error")
        await websocket.close()

    wireup.integration.fastapi.setup(container, app, middleware_mode=middleware_mode)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            assert websocket.receive_text() == "wireup-error"


@pytest.mark.parametrize("middleware_mode", [True, False], ids=["middleware_mode=True", "middleware_mode=False"])
def test_websocket_scoped_route_get_request_container_unavailable(*, middleware_mode: bool) -> None:
    @injectable(lifetime="scoped")
    class ScopedWsContext:
        def __init__(self) -> None:
            self.id = uuid4().hex

    app = FastAPI()
    container = wireup.create_async_container(injectables=[ScopedWsContext, wireup.integration.fastapi])

    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket, _ctx: Injected[ScopedWsContext]) -> None:
        await websocket.accept()
        try:
            get_request_container()
        except WireupError:
            await websocket.send_text("wireup-error")
        await websocket.close()

    wireup.integration.fastapi.setup(container, app, middleware_mode=middleware_mode)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            assert websocket.receive_text() == "wireup-error"


def test_get_request_container_error_message_has_actionable_hints() -> None:
    with pytest.raises(WireupError) as exc_info:
        get_request_container()

    msg = str(exc_info.value)
    assert "middleware ordering issue" in msg
    assert "middleware_mode=True" in msg
    assert "HTTP-only" in msg


def test_http_middleware_before_setup_can_access_get_request_container() -> None:
    class ProbeMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):  # type: ignore[override]
            req_from_wireup = await get_request_container().get(Request)
            request.state.probe = req_from_wireup.url.path == request.url.path
            return await call_next(request)

    app = FastAPI()
    app.add_middleware(ProbeMiddleware)
    container = wireup.create_async_container(injectables=[wireup.integration.fastapi])

    @app.get("/")
    async def endpoint(request: Request) -> Dict[str, bool]:
        return {"probe_ok": request.state.probe}

    wireup.integration.fastapi.setup(container, app, middleware_mode=True)

    with TestClient(app) as client:
        res = client.get("/")

    assert res.status_code == 200
    assert res.json() == {"probe_ok": True}


def test_http_middleware_after_setup_hits_ordering_error() -> None:
    class ProbeMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):  # type: ignore[override]
            try:
                get_request_container()
            except WireupError as e:
                request.state.err = str(e)
            return await call_next(request)

    app = FastAPI()
    container = wireup.create_async_container(injectables=[wireup.integration.fastapi])
    wireup.integration.fastapi.setup(container, app, middleware_mode=True)
    app.add_middleware(ProbeMiddleware)

    @app.get("/")
    async def endpoint(request: Request) -> Dict[str, str]:
        return {"error": request.state.err}

    with TestClient(app) as client:
        res = client.get("/")

    assert res.status_code == 200
    assert "middleware ordering issue" in res.json()["error"]


def test_websocket_scoped_context_does_not_leak_between_overlapping_connections() -> None:
    @injectable(lifetime="scoped")
    class ScopedWsContext:
        def __init__(self) -> None:
            self.id = uuid4().hex

    app = FastAPI()
    container = wireup.create_async_container(injectables=[ScopedWsContext, wireup.integration.fastapi])

    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket, scoped: Injected[ScopedWsContext]) -> None:
        await websocket.accept()
        _ = await websocket.receive_text()
        await websocket.send_text(scoped.id)
        await websocket.close()

    wireup.integration.fastapi.setup(container, app, middleware_mode=False)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws_1, client.websocket_connect("/ws") as ws_2:
            ws_1.send_text("one")
            ws_2.send_text("two")
            id_1 = ws_1.receive_text()
            id_2 = ws_2.receive_text()

    assert id_1 != id_2


def test_websocket_scoped_context_concurrent_connections_do_not_leak() -> None:
    @injectable(lifetime="scoped")
    class ScopedWsContext:
        def __init__(self) -> None:
            self.id = uuid4().hex

    app = FastAPI()
    container = wireup.create_async_container(injectables=[ScopedWsContext, wireup.integration.fastapi])

    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket, scoped: Injected[ScopedWsContext]) -> None:
        await websocket.accept()
        _ = await websocket.receive_text()
        await websocket.send_text(scoped.id)
        await websocket.close()

    wireup.integration.fastapi.setup(container, app, middleware_mode=False)

    barrier = Barrier(2)
    ids: list[str] = []

    def _client_task() -> None:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                barrier.wait()
                websocket.send_text("go")
                ids.append(websocket.receive_text())

    t1 = Thread(target=_client_task)
    t2 = Thread(target=_client_task)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(ids) == 2
    assert ids[0] != ids[1]


def test_websocket_exception_path_does_not_poison_next_scope() -> None:
    @injectable(lifetime="scoped")
    class ScopedWsContext:
        def __init__(self) -> None:
            self.id = uuid4().hex

    app = FastAPI()
    container = wireup.create_async_container(injectables=[ScopedWsContext, wireup.integration.fastapi])

    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket, scoped: Injected[ScopedWsContext]) -> None:
        await websocket.accept()
        msg = await websocket.receive_text()
        if msg == "boom":
            raise RuntimeError("boom")
        await websocket.send_text(scoped.id)
        await websocket.close()

    wireup.integration.fastapi.setup(container, app, middleware_mode=False)

    with TestClient(app) as client:
        with pytest.raises(RuntimeError, match="boom"):
            with client.websocket_connect("/ws") as websocket:
                websocket.send_text("boom")
                websocket.receive_text()

        with client.websocket_connect("/ws") as websocket_1:
            websocket_1.send_text("ok")
            ok_id_1 = websocket_1.receive_text()

        with client.websocket_connect("/ws") as websocket_2:
            websocket_2.send_text("ok")
            ok_id_2 = websocket_2.receive_text()

    assert ok_id_1 != ok_id_2


async def test_current_request_service(client: TestClient):
    async def _make_request():
        request_id = uuid.uuid4().hex
        response = await anyio.to_thread.run_sync(
            lambda: client.get("/current-request", params={"foo": request_id}, headers={"X-Request-Id": request_id})
        )
        assert response.status_code == 200
        assert response.json() == {"foo": request_id, "request_id": request_id}

    await asyncio.gather(*(_make_request() for _ in range(100)))


@pytest.mark.parametrize("t", [Request, WebSocket])
async def test_raises_request_outside_of_scope(app: FastAPI, t: Any) -> None:
    with pytest.raises(WireupError, match=f"{t.__name__} in Wireup is only available."):
        async with get_app_container(app).enter_scope() as scoped:
            await scoped.get(t)


def test_cbr(client: TestClient):
    for i in range(1, 5):
        response = client.get("/cbr")
        assert response.status_code == 200
        assert response.json() == {"counter": i, "random": 4}


async def test_closes_container_on_lifespan_close() -> None:
    cleanup_done = False

    class Thing: ...

    @injectable
    def make_thing() -> Iterator[Thing]:
        yield Thing()
        nonlocal cleanup_done
        cleanup_done = True

    app = FastAPI()
    container = wireup.create_async_container(injectables=[make_thing])

    @app.get("/")
    async def _(thing: Injected[Thing]) -> Dict[str, Any]:
        assert isinstance(thing, Thing)
        return {}

    wireup.integration.fastapi.setup(container, app, middleware_mode=False)
    assert len(app.user_middleware) == 0

    with TestClient(app) as client:
        client.get("/")

    assert cleanup_done


async def test_executes_fastapi_lifespan() -> None:
    cleanup_done = False

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield

        nonlocal cleanup_done
        cleanup_done = True

    app = FastAPI(lifespan=lifespan)
    container = wireup.create_async_container(
        injectables=[fastapi_test_services, shared_services, wireup.integration.fastapi]
    )

    wireup.integration.fastapi.setup(container, app)

    with TestClient(app) as _:
        ...

    assert cleanup_done


async def test_middleware_disabled_does_not_add_middleware() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[RandomService])

    @app.get("/")
    async def _(random: Injected[RandomService]) -> Dict[str, Any]:
        return {"random": random.get_random()}

    wireup.integration.fastapi.setup(container, app, middleware_mode=False)
    assert len(app.user_middleware) == 0

    with TestClient(app) as client:
        res = client.get("/")
        assert res.json() == {"random": 4}


async def test_overrides_in_class_based_handlers() -> None:
    app = create_app(expose_container_in_middleware=True)

    class FakeRandomService(RandomService):
        def get_random(self) -> int:
            return 100

    new_instance = FakeRandomService()

    with get_app_container(app).override.injectable(RandomService, new=new_instance), TestClient(app) as client:
        res = client.get("/cbr")
        assert res.json() == {"counter": 1, "random": 100}

        assert await get_app_container(app).get(RandomService) is new_instance


def test_class_based_handlers_work_across_lifespan_restarts() -> None:
    app = create_app(expose_container_in_middleware=True)

    with TestClient(app) as client:
        first = client.get("/cbr").json()

    with TestClient(app) as client:
        second = client.get("/cbr").json()

    cbr_routes = [route for route in app.routes if isinstance(route, APIRoute) and route.path == "/cbr/"]

    assert first == {"counter": 1, "random": 4}
    assert second == {"counter": 2, "random": 4}
    assert len(cbr_routes) == 1


def test_injects_background_tasks() -> None:
    task_result: list[str] = []

    def write_logs(name: str, random_service: Injected[RandomService]) -> None:
        task_result.append(f"{name}:{random_service.get_random()}")

    app = FastAPI()
    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.fastapi])

    @app.get("/")
    async def hello(tasks: BackgroundTasks, wireup_task: Injected[WireupTask]) -> Dict[str, Any]:
        tasks.add_task(wireup_task(write_logs), "fastapi")
        return {}

    wireup.integration.fastapi.setup(container, app)

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert task_result == ["fastapi:4"]


def test_background_task_uses_different_scope_than_request() -> None:
    ids: dict[str, str] = {}

    @injectable(lifetime="scoped")
    class ScopedContext:
        def __init__(self) -> None:
            self.id = uuid4().hex

    def write_logs(scoped_context: Injected[ScopedContext]) -> None:
        ids["task"] = scoped_context.id

    app = FastAPI()
    container = wireup.create_async_container(
        injectables=[ScopedContext, shared_services, wireup.integration.fastapi],
    )

    @app.get("/")
    async def hello(tasks: BackgroundTasks, scoped_context: Injected[ScopedContext], wireup_task: Injected[WireupTask]):
        ids["request"] = scoped_context.id
        tasks.add_task(wireup_task(write_logs))
        return {}

    wireup.integration.fastapi.setup(container, app)

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert ids["request"] != ids["task"]


def test_missing_setup_raises_actionable_error_for_injected_route_parameter() -> None:
    app = FastAPI()

    @app.get("/")
    async def endpoint(random_service: Injected[RandomService]) -> Dict[str, int]:
        return {"number": random_service.get_random()}

    with pytest.raises(WireupError, match="Injection is not set up correctly"):
        with TestClient(app) as client:
            client.get("/")


def test_setup_called_before_adding_routes_injects_at_startup() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.fastapi])
    wireup.integration.fastapi.setup(container, app)

    @app.get("/")
    async def endpoint(random_service: Injected[RandomService]) -> Dict[str, int]:
        return {"number": random_service.get_random()}

    with TestClient(app) as client:
        res = client.get("/")

    assert res.status_code == 200
    assert res.json() == {"number": 4}


def test_setup_allows_reusing_container_across_apps() -> None:
    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.fastapi])
    app_one = FastAPI()
    app_two = FastAPI()

    wireup.integration.fastapi.setup(container, app_one)
    wireup.integration.fastapi.setup(container, app_two)


def test_lifespan_injection_pass_does_not_rewrap_routes_already_injected_at_setup() -> None:
    app = FastAPI()
    container = wireup.create_async_container(injectables=[shared_services, wireup.integration.fastapi])

    @app.get("/")
    async def endpoint(random_service: Injected[RandomService]) -> Dict[str, int]:
        return {"number": random_service.get_random()}

    wireup.integration.fastapi.setup(container, app)
    call_after_setup = _get_http_route_call(app, "/")

    with TestClient(app) as client:
        res = client.get("/")

    call_after_startup = _get_http_route_call(app, "/")
    assert res.status_code == 200
    assert call_after_startup is call_after_setup
    assert _wireup_wrapper_count(call_after_startup) == 1


def test_class_based_lifespan_dual_pass_does_not_double_wrap_routes() -> None:
    app = FastAPI()
    container = wireup.create_async_container(
        injectables=[fastapi_test_services, shared_services, wireup.integration.fastapi],
    )

    @app.get("/")
    async def endpoint(random_service: Injected[RandomService]) -> Dict[str, int]:
        return {"number": random_service.get_random()}

    wireup.integration.fastapi.setup(container, app, class_based_handlers=[cbr.MyClassBasedRoute])

    with TestClient(app) as client:
        res = client.get("/")

    call_after_startup = _get_http_route_call(app, "/")
    assert res.status_code == 200
    assert _wireup_wrapper_count(call_after_startup) == 1


# ---- Set[T] collection injection through a FastAPI route ----


class _RouteCache:
    def name(self) -> str:
        return "base"


@injectable(as_type=_RouteCache, qualifier="redis")
class _RouteRedisCache(_RouteCache):
    def name(self) -> str:
        return "redis"


@injectable(as_type=_RouteCache, qualifier="memory")
class _RouteMemoryCache(_RouteCache):
    def name(self) -> str:
        return "memory"


def test_fastapi_route_injects_set_of_impls() -> None:
    app = FastAPI()
    container = wireup.create_async_container(
        injectables=[_RouteRedisCache, _RouteMemoryCache, wireup.integration.fastapi],
    )

    @app.get("/caches")
    async def list_caches(caches: Injected[Set[_RouteCache]]) -> Dict[str, Any]:
        return {"names": sorted(cache.name() for cache in caches)}

    wireup.integration.fastapi.setup(container, app)

    with TestClient(app) as client:
        res = client.get("/caches")

    assert res.status_code == 200
    assert res.json() == {"names": ["memory", "redis"]}
