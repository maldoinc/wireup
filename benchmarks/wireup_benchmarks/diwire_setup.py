from typing import Dict

import fastapi
from diwire import Container, Injected, Lifetime, Scope, resolver_context

from wireup_benchmarks import services
from wireup_benchmarks.services import A, B, C, D, E, F, G, H, I, Settings

container = Container()

container.add_factory(lambda: Settings(10), provides=Settings, scope=Scope.APP, lifetime=Lifetime.SCOPED)
container.add_factory(services.make_a, provides=A, scope=Scope.APP, lifetime=Lifetime.SCOPED)
container.add(B, scope=Scope.APP, lifetime=Lifetime.SCOPED)

for service_type in (C, D, E, F, G):
    container.add(service_type, scope=Scope.REQUEST, lifetime=Lifetime.SCOPED)

container.add_generator(services.make_h, provides=H, scope=Scope.REQUEST, lifetime=Lifetime.SCOPED)
container.add_generator(services.make_i, provides=I, scope=Scope.REQUEST, lifetime=Lifetime.SCOPED)
resolver_context.set_fallback_container(container)

router = fastapi.APIRouter()


@router.get("/diwire/singleton")
@resolver_context.inject(scope=Scope.REQUEST)
async def diwire_singleton(a: Injected[A], b: Injected[B]) -> Dict[str, str]:
    services.record_request("singleton")
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/diwire/scoped")
@resolver_context.inject(scope=Scope.REQUEST)
async def diwire_scoped(
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
