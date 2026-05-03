import dishka
import fastapi
from dishka.integrations.fastapi import FromDishka, inject

from wireup_benchmarks import services
from wireup_benchmarks.services import A, B, C, D, E, F, G, H, I, Settings, make_a, make_h, make_i

provider = dishka.Provider(scope=dishka.Scope.APP)
provider.provide(lambda: Settings(10), provides=Settings)
provider.provide(make_a)
provider.provide(B)
provider.provide(C, scope=dishka.Scope.REQUEST)
provider.provide(D, scope=dishka.Scope.REQUEST)
provider.provide(E, scope=dishka.Scope.REQUEST)
provider.provide(F, scope=dishka.Scope.REQUEST)
provider.provide(G, scope=dishka.Scope.REQUEST)
provider.provide(make_h, scope=dishka.Scope.REQUEST)
provider.provide(make_i, scope=dishka.Scope.REQUEST)
container = dishka.make_async_container(provider)
router = fastapi.APIRouter()


@router.get("/dishka/singleton")
@inject
async def dishka_singleton(a: FromDishka[A], b: FromDishka[B]) -> dict[str, str]:
    services.record_request("singleton")
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/dishka/scoped")
@inject
async def dishka_scoped(
    c: FromDishka[C],
    cc: FromDishka[C],
    ccc: FromDishka[C],
    d: FromDishka[D],
    dd: FromDishka[D],
    e: FromDishka[E],
    f: FromDishka[F],
    g: FromDishka[G],
    h: FromDishka[H],
    i: FromDishka[I],
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
