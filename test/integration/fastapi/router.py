import functools
from typing import Any, Dict

import fastapi
from fastapi import APIRouter, Depends, Request, WebSocket
from typing_extensions import Annotated
from wireup import Inject, Injected
from wireup.integration.fastapi import get_request_container
from wireup.ioc.types import AnyCallable

from test.integration.fastapi.services import ServiceUsingFastapiRequest, WebsocketInjectedGreeterService, WSService
from test.shared.shared_services.greeter import GreeterService
from test.shared.shared_services.rand import RandomService
from test.shared.shared_services.scoped import ScopedService, ScopedServiceDependency

router = APIRouter()


def get_lucky_number() -> int:
    get_lucky_number._called += 1  # type: ignore[reportFunctionMemberAccess]
    return 42


@router.get("/lucky-number")
async def lucky_number_route(
    random_service: Injected[RandomService], lucky_number: Annotated[int, Depends(get_lucky_number)]
):
    return {"number": random_service.get_random(), "lucky_number": lucky_number}


@router.get("/rng")
async def rng_route(random_service: Injected[RandomService]):
    return {"number": random_service.get_random()}


@router.get("/rng/depends")
async def inject_via_depends(
    random_service: Annotated[RandomService, Depends(RandomService)],
) -> Dict[str, int]:
    return {"number": random_service.get_random()}


@router.get("/params")
async def params_route(
    foo: Annotated[str, Inject(config="foo")], foo_foo: Annotated[str, Inject(expr="${foo}-${foo}")]
):
    return {"foo": foo, "foo_foo": foo_foo}


@router.get("/current-request")
async def curr_request(_request: Request, req: Injected[ServiceUsingFastapiRequest]) -> Dict[str, Any]:
    return {"foo": req.req.query_params["foo"], "request_id": req.req.headers["X-Request-Id"]}


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    greeter: Injected[GreeterService],
    scoped_service: Injected[ScopedService],
    scoped_service2: Injected[ScopedService],
    scoped_service_dependency: Injected[ScopedServiceDependency],
    ws_service: Injected[WSService],
):
    assert isinstance(await get_request_container().get(WebSocket), WebSocket)
    assert scoped_service is scoped_service2
    assert scoped_service.other is scoped_service_dependency

    assert ws_service.ws is websocket

    await websocket.accept()
    data = await websocket.receive_text()
    await websocket.send_text(greeter.greet(data))
    await websocket.close()


@router.websocket("/ws/no-websocket-in-signature")
async def websocket_endpoint_wireup(
    greeter: Injected[GreeterService],
    scoped_service: Injected[ScopedService],
    scoped_service2: Injected[ScopedService],
    scoped_service_dependency: Injected[ScopedServiceDependency],
    ws_service: Injected[WSService],
):
    assert isinstance(await get_request_container().get(WebSocket), WebSocket)
    assert scoped_service is scoped_service2
    assert scoped_service.other is scoped_service_dependency

    websocket = ws_service.ws
    await websocket.accept()
    data = await websocket.receive_text()
    await websocket.send_text(greeter.greet(data))
    await websocket.close()


@router.websocket("/ws_in_service")
async def injected_websocket_endpoint(greeter: Injected[WebsocketInjectedGreeterService]):
    await greeter.greet()


@router.get("/scoped")
async def scoped_route(
    scoped_service: Injected[ScopedService],
    scoped_service2: Injected[ScopedService],
    scoped_service_dependency: Injected[ScopedServiceDependency],
):
    assert scoped_service is scoped_service2
    assert scoped_service.other is scoped_service_dependency


def require_not_bob(fn: AnyCallable) -> AnyCallable:
    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = await get_request_container().get(Request)

        if request.query_params.get("name") == "Bob":
            raise fastapi.exceptions.HTTPException(status_code=401, detail="Bob is not allowed")
        return await fn(*args, **kwargs)

    return wrapper


@router.get("/401_for_bob")
@require_not_bob
async def decorated_fn_route(random_service: Injected[RandomService]):
    return {"number": random_service.get_random()}
