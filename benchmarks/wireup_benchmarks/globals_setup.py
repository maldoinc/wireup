import contextlib

import fastapi

from wireup_benchmarks import services
from wireup_benchmarks.services import A, B, C, D, E, F, G, H, I

settings = services.Settings()
a = services.A(start=settings.start)
b = services.B(a=a)


router = fastapi.APIRouter()


@router.get("/globals/singleton")
async def fastapi_singleton() -> dict[str, str]:
    services.record_request("singleton")
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/globals/scoped")
async def globals_scoped() -> dict[str, str]:
    services.record_request("scoped")
    c = C()
    d = D(c=c)
    e = E(c=c, d=d)
    f = F(c=c, d=d, e=e)
    g = G(c=c, d=d, e=e, f=f)
    with contextlib.contextmanager(services.make_h)(c=c, d=d) as h:
        assert isinstance(h, H)
    async with contextlib.asynccontextmanager(services.make_i)(e=e, f=f) as i:
        assert isinstance(i, I)

    assert isinstance(c, C)
    assert isinstance(d, D)
    assert isinstance(e, E)
    assert isinstance(f, F)
    assert isinstance(g, G)
    assert isinstance(h, H)
    assert isinstance(i, I)
    return {}
