from dataclasses import dataclass

from aiohttp import web
from wireup._annotations import Injected
from wireup.integration.aiohttp import get_request_container, route

from test.integration.aiohttp.services import RequestContext
from test.shared.shared_services.greeter import GreeterService

router = web.RouteTableDef()


@router.get("/greeting")
@route
async def hello_world(_request: web.Request, greeter: Injected[GreeterService]) -> web.Response:
    return web.json_response({"greeting": greeter.greet(_request.query.get("name", "world"))})


@router.get("/inject_request")
@route
async def inject_request(_request: web.Request, req_context: Injected[RequestContext]) -> web.Response:
    assert _request is req_context.request
    assert req_context is await get_request_container().get(RequestContext)

    return web.json_response()


@router.get("/webview")
@dataclass
class WebViewRoute(web.View):
    _request: web.Request
    greeter: Injected[GreeterService]

    async def get(self) -> web.Response:
        return web.json_response({"greeting": self.greeter.greet("webview")})
