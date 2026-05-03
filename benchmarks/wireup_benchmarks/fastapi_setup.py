from functools import lru_cache
from collections.abc import AsyncIterator, Iterator

import fastapi
from typing import Annotated

from wireup_benchmarks import services
from wireup_benchmarks.services import A, B, C, D, E, F, G, H, I, Settings, make_h, make_i


# This is the recommended way to do this in the docs but outright kills performance.
# Creating and storing objects in app.state is faster but at that point you're not really using fastapi Depends.
@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_a(settings: Annotated[Settings, fastapi.Depends(get_settings)]) -> A:
    return A(start=settings.start)


@lru_cache
def get_b(a: Annotated[A, fastapi.Depends(get_a)]) -> B:
    return B(a=a)


async def get_c() -> C:
    return C()


async def get_d(
    c: Annotated[C, fastapi.Depends(get_c)],
) -> D:
    return D(c=c)


async def get_e(
    c: Annotated[C, fastapi.Depends(get_c)],
    d: Annotated[D, fastapi.Depends(get_d)],
) -> E:
    return E(c=c, d=d)


async def get_f(
    c: Annotated[C, fastapi.Depends(get_c)],
    d: Annotated[D, fastapi.Depends(get_d)],
    e: Annotated[E, fastapi.Depends(get_e)],
) -> F:
    return F(c=c, d=d, e=e)


async def get_g(
    c: Annotated[C, fastapi.Depends(get_c)],
    d: Annotated[D, fastapi.Depends(get_d)],
    e: Annotated[E, fastapi.Depends(get_e)],
    f: Annotated[F, fastapi.Depends(get_f)],
) -> G:
    return G(c=c, d=d, e=e, f=f)


def get_h(c: Annotated[C, fastapi.Depends(get_c)], d: Annotated[D, fastapi.Depends(get_d)]) -> Iterator[H]:
    yield from make_h(c=c, d=d)


async def get_i(e: Annotated[E, fastapi.Depends(get_e)], f: Annotated[F, fastapi.Depends(get_f)]) -> AsyncIterator[I]:
    async for i in make_i(e=e, f=f):
        yield i


router = fastapi.APIRouter()


@router.get("/fastapi/singleton")
async def fastapi_singleton(
    a: Annotated[A, fastapi.Depends(get_a)], b: Annotated[B, fastapi.Depends(get_b)]
) -> dict[str, str]:
    services.record_request("singleton")
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/fastapi/scoped")
async def fastapi_scoped(
    c: Annotated[C, fastapi.Depends(get_c)],
    cc: Annotated[C, fastapi.Depends(get_c)],
    ccc: Annotated[C, fastapi.Depends(get_c)],
    d: Annotated[D, fastapi.Depends(get_d)],
    dd: Annotated[D, fastapi.Depends(get_d)],
    e: Annotated[E, fastapi.Depends(get_e)],
    f: Annotated[F, fastapi.Depends(get_f)],
    g: Annotated[G, fastapi.Depends(get_g)],
    h: Annotated[H, fastapi.Depends(get_h)],
    i: Annotated[I, fastapi.Depends(get_i)],
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
