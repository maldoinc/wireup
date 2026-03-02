import contextlib
from typing import Dict

import aioinject
import fastapi
from aioinject import Injected
from aioinject.ext.fastapi import FastAPIExtension, inject

from wireup_benchmarks import services
from wireup_benchmarks.services import A, B, C, D, E, F, G, H, I, Settings, make_a, make_h, make_i

container = aioinject.Container(extensions=[FastAPIExtension()])
container.register(
    aioinject.Singleton(lambda: Settings(10), Settings),
    aioinject.Singleton(make_a, A),
    aioinject.Singleton(B),
    aioinject.Scoped(C),
    aioinject.Scoped(D),
    aioinject.Scoped(E),
    aioinject.Scoped(F),
    aioinject.Scoped(G),
    aioinject.Scoped(contextlib.contextmanager(make_h), H),
    aioinject.Scoped(contextlib.asynccontextmanager(make_i), I),
)

router = fastapi.APIRouter()


@router.get("/aioinject/singleton")
@inject
async def wireup_singleton(a: Injected[A], b: Injected[B]) -> Dict[str, str]:
    services.record_request("singleton")
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/aioinject/scoped")
@inject
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
