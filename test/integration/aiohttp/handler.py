from aiohttp import web
from wireup import Injected
from wireup.integration.aiohttp import route

from test.shared.shared_services.greeter import GreeterService


class WireupTestHandler:
    router = web.RouteTableDef()

    def __init__(self, greeter: GreeterService) -> None:
        self.greeter = greeter
        self.counter = 0

    @router.get("/handler/greet")
    @route
    async def get_thing(self, request: web.Request, greeter: Injected[GreeterService]) -> web.Response:
        assert greeter is self.greeter

        self.counter += 1

        return web.json_response(
            {
                "greeting": self.greeter.greet(request.query.get("name", "world")),
                "counter": self.counter,
            }
        )
