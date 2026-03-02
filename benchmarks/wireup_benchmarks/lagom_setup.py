from typing import Dict, Iterator

import fastapi
from lagom import Container, Singleton, context_dependency_definition
from lagom.integrations.fast_api import FastApiIntegration

from wireup_benchmarks import services
from wireup_benchmarks.services import A, B, C, D, E, F, G, H, I, Settings

container = Container()

# Singletons - define with Singleton wrapper
container[Settings] = Singleton(Settings)
container[A] = Singleton(lambda c: A(c[Settings].start))
container[B] = Singleton(B)

# Scoped services (request-level singletons) - just define types
container[C] = C
container[D] = D
container[E] = E
container[F] = F
container[G] = G


# For generator-based services (H), use context_dependency_definition
@context_dependency_definition(container)
def build_h(c: Container) -> Iterator[H]:
    yield H(c[C], c[D])


# I is an async generator in other frameworks, but lagom doesn't support async
# Use sync context_dependency_definition as the closest equivalent
@context_dependency_definition(container)
def build_i(c: Container) -> Iterator[I]:
    yield I(c[E], c[F])


router = fastapi.APIRouter()
deps = FastApiIntegration(container, request_singletons=[C, D, E, F, G], request_context_singletons=[H, I])


@router.get("/lagom/singleton")
async def lagom_singleton(
    a=deps.depends(A),
    b=deps.depends(B),
) -> Dict[str, str]:
    services.record_request("singleton")
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/lagom/scoped")
async def lagom_scoped(
    c=deps.depends(C),
    cc=deps.depends(C),
    ccc=deps.depends(C),
    d=deps.depends(D),
    dd=deps.depends(D),
    e=deps.depends(E),
    f=deps.depends(F),
    g=deps.depends(G),
    h=deps.depends(H),
    i=deps.depends(I),
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
