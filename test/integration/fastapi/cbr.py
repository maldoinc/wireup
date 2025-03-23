from typing import Any, Dict

import fastapi
from wireup.integration.fastapi import controller

from test.shared.shared_services.rand import RandomService

router = fastapi.APIRouter()


@controller(router)
class MyController:
    def __init__(self, random_service: RandomService) -> None:
        self.rng = random_service
        self.counter = 0

    @router.get("/cbr")
    def get_cbr(self) -> Dict[str, Any]:
        self.counter += 1
        return {"counter": self.counter, "random": self.rng.get_random()}
