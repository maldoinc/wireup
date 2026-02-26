import asyncio
import contextlib
import uuid
from typing import Any, AsyncIterator, Dict, Iterator
from uuid import uuid4

import anyio.to_thread
import pytest
import wireup
import wireup.integration
import wireup.integration.fastapi
from fastapi import BackgroundTasks, FastAPI, Request, WebSocket
from fastapi.testclient import TestClient
from wireup._annotations import Injected, injectable
from wireup.errors import WireupError
from wireup.integration.fastapi import WireupTask, get_app_container

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


def test_injects_service(client: TestClient):
    get_lucky_number._called = 0  # type: ignore[reportFunctionMemberAccess]
    response = client.get("/lucky-number")
    assert response.status_code == 200
    assert response.json() == {"number": 4, "lucky_number": 42}
    # Raise if this will be invoked more than once
    # That would be the case if wireup also "unwraps" and tries
    # to resolve dependencies it doesn't own.
    assert get_lucky_number._called == 1  # type: ignore[reportFunctionMemberAccess]


@pytest.mark.parametrize("endpoint", ["/scoped", "/scoped/wireup_injected"])
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


def test_request_container_in_decorator(client: TestClient):
    response = client.get("/401_for_bob?name=Bob")
    assert response.status_code == 401

    response = client.get("/401_for_bob?name=NotBob")
    assert response.json() == {"number": 4}


@pytest.mark.parametrize("endpoint", ["/ws", "/ws/wireup_injected", "/ws_in_service", "/ws/no-websocket-in-signature"])
def test_websocket(client: TestClient, endpoint: str):
    with client.websocket_connect(endpoint) as websocket:
        websocket.send_text("World")
        data = websocket.receive_text()
        assert data == "Hello World"


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
