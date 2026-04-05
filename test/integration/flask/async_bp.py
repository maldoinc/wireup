import flask
from wireup import Injected

from test.shared.shared_services.async_service import AsyncRandomService

async_bp = flask.Blueprint("async_bp", "async_bp")


@async_bp.get("/async")
async def async_route(random: Injected[AsyncRandomService]):
    return {"lucky_number": await random.get_random()}
