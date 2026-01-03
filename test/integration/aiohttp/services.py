from dataclasses import dataclass

from aiohttp import web
from wireup._annotations import injectable


@injectable(lifetime="scoped")
@dataclass
class RequestContext:
    request: web.Request
