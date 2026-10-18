import fastapi
import wireup
from wireup import Injected
from wireup.integration.fastapi import WireupRoute

from wireup_benchmarks import services
from wireup_benchmarks.services import A, B, C, D, E, F, G, H, I

router = fastapi.APIRouter(route_class=WireupRoute)
container = wireup.create_async_container(
    services=[
        wireup.service(services.Settings),
        wireup.service(services.make_a),
        wireup.service(services.B),
        wireup.service(services.C, lifetime="scoped"),
        wireup.service(services.D, lifetime="scoped"),
        wireup.service(services.E, lifetime="scoped"),
        wireup.service(services.F, lifetime="scoped"),
        wireup.service(services.G, lifetime="scoped"),
        wireup.service(services.make_h, lifetime="scoped"),
        wireup.service(services.make_i, lifetime="scoped"),
    ],
    parameters={"start": 10},
)


@router.get("/wireup/singleton")
async def wireup_singleton(a: Injected[A], b: Injected[B]) -> dict[str, str]:
    services.record_request("singleton")
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/wireup/scoped")
async def wireup_scoped(
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
) -> dict[str, str]:
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
