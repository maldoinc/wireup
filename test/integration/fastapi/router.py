from typing import Any, Dict

from fastapi import APIRouter, Depends, Request, WebSocket
from typing_extensions import Annotated
from wireup.annotation import Inject, Injected

from test.integration.fastapi.services import ServiceUsingFastapiRequest
from test.shared.shared_services.greeter import GreeterService
from test.shared.shared_services.rand import RandomService
from test.shared.shared_services.scoped import ScopedService, ScopedServiceDependency

router = APIRouter()


def get_lucky_number() -> int:
    # Raise if this will be invoked more than once
    # That would be the case if wireup also "unwraps" and tries
    # to resolve dependencies it doesn't own.
    if hasattr(get_lucky_number, "_called"):
        raise Exception("Lucky Number was already invoked")

    get_lucky_number._called = True  # type: ignore[reportFunctionMemberAccess]
    return 42


@router.get("/lucky-number")
async def lucky_number_route(
    random_service: Injected[RandomService], lucky_number: Annotated[int, Depends(get_lucky_number)]
):
    return {"number": random_service.get_random(), "lucky_number": lucky_number}


@router.get("/rng")
async def rng_route(random_service: Injected[RandomService]):
    return {"number": random_service.get_random()}


@router.get("/params")
async def params_route(foo: Annotated[str, Inject(param="foo")], foo_foo: Annotated[str, Inject(expr="${foo}-${foo}")]):
    return {"foo": foo, "foo_foo": foo_foo}


@router.get("/raise-unknown")
async def raise_unknown(_unknown_service: Injected[None]):
    return {"msg": "Hello World"}


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
):
    assert scoped_service is scoped_service2
    assert scoped_service.other is scoped_service_dependency

    await websocket.accept()
    data = await websocket.receive_text()
    await websocket.send_text(greeter.greet(data))
    await websocket.close()


@router.get("/scoped")
async def scoped_route(
    scoped_service: Injected[ScopedService],
    scoped_service2: Injected[ScopedService],
    scoped_service_dependency: Injected[ScopedServiceDependency],
):
    assert scoped_service is scoped_service2
    assert scoped_service.other is scoped_service_dependency
