from typing import Any, Dict

import fastapi
from wireup.integration.fastapi import WireupRoute

from test.shared.shared_services.rand import RandomService


class MyClassBasedRoute:
    router = fastapi.APIRouter(route_class=WireupRoute)

    def __init__(self, random_service: RandomService) -> None:
        self.rng = random_service
        self.counter = 0

    @router.get("/cbr")
    def get_cbr(self) -> Dict[str, Any]:
        self.counter += 1
        return {"counter": self.counter, "random": self.rng.get_random()}
