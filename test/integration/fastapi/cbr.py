from typing import Any

import fastapi
from fastapi import Depends
from wireup._annotations import Injected

from test.shared.shared_services.rand import RandomService

_router_dep_called = False


def _record_router_dep():
    global _router_dep_called  # noqa: PLW0603
    _router_dep_called = True


class CbrWithRouterDependency:
    router = fastapi.APIRouter(
        prefix="/cbr-dep",
        dependencies=[Depends(_record_router_dep)],
    )

    @router.get("/")
    def handler(self) -> dict[str, Any]:
        return {"ok": True}


class MyClassBasedRoute:
    router = fastapi.APIRouter(prefix="/cbr")

    def __init__(self, random_service: RandomService) -> None:
        self.rng = random_service
        self.counter = 0

    @router.get("/")
    def get_cbr(self, random_service: Injected[RandomService]) -> dict[str, Any]:
        assert random_service is self.rng
        self.counter += 1

        return {"counter": self.counter, "random": self.rng.get_random()}
