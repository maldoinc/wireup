from typing import Dict

import fastapi
from wireup import Injected
from wireup.integration.fastapi import WireupRoute

from wireup_benchmarks import services
from wireup_benchmarks.services import A, B, C, D, E, F, G, H, I


class WireupSingletonBenchController:
    __slots__ = ("a", "b")
    router = fastapi.APIRouter(prefix="/wireup_cbr", route_class=WireupRoute)

    def __init__(self, a: A, b: B) -> None:
        self.a = a
        self.b = b

    @router.get("/singleton")
    async def wireup_singleton(self) -> Dict[str, str]:
        services.record_request("singleton")
        assert self.a.start == 10
        assert isinstance(self.a, A)
        assert isinstance(self.b, B)
        return {}


class WireupScopedBenchController:
    router = fastapi.APIRouter(prefix="/wireup_cbr", route_class=WireupRoute)

    @router.get("/scoped")
    async def wireup_scoped(
        self,
        c: Injected[C],
        cc: Injected[C],
        ccc: Injected[C],
        d: Injected[D],
        dd: Injected[D],
        e: Injected[E],
        f: Injected[F],
        g: Injected[G],
        h: Injected[H],
        i: Injected[I],
    ) -> Dict[str, str]:
        services.record_request("scoped")
        assert isinstance(c, C)
        assert c is cc
        assert cc is ccc

        assert isinstance(d, D)
        assert isinstance(e, E)
        assert isinstance(f, F)
        assert isinstance(g, G)
        assert isinstance(h, H)
        assert isinstance(i, I)
        assert d is dd
        return {}
