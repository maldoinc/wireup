from typing import Any, Dict

import fastapi
from wireup._annotations import Injected

from test.shared.shared_services.rand import RandomService


class MyClassBasedRoute:
    router = fastapi.APIRouter(prefix="/cbr")

    def __init__(self, random_service: RandomService) -> None:
        self.rng = random_service
        self.counter = 0

    @router.get("/")
    def get_cbr(self, random_service: Injected[RandomService]) -> Dict[str, Any]:
        assert random_service is self.rng
        self.counter += 1

        return {"counter": self.counter, "random": self.rng.get_random()}
