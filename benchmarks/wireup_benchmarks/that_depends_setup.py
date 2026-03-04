from typing_extensions import Annotated

from fastapi import APIRouter, Depends
from that_depends import BaseContainer, providers
from that_depends.providers.context_resources import ContextScopes

from wireup_benchmarks import services


def _c_resource():
    yield services.C()


def _d_resource(c):
    yield services.D(c=c)


def _e_resource(c, d):
    yield services.E(c=c, d=d)


def _f_resource(c, d, e):
    yield services.F(c=c, d=d, e=e)


def _g_resource(c, d, e, f):
    yield services.G(c=c, d=d, e=e, f=f)


class Container(BaseContainer):
    default_scope = ContextScopes.REQUEST
    settings = providers.Singleton(services.Settings)
    a = providers.Singleton(services.make_a, settings=settings)
    b = providers.Singleton(services.B, a=a)

    c = providers.ContextResource(_c_resource).with_config(scope=ContextScopes.REQUEST, strict_scope=True)
    d = providers.ContextResource(_d_resource, c=c).with_config(scope=ContextScopes.REQUEST, strict_scope=True)
    e = providers.ContextResource(_e_resource, c=c, d=d).with_config(scope=ContextScopes.REQUEST, strict_scope=True)
    f = providers.ContextResource(_f_resource, c=c, d=d, e=e).with_config(
        scope=ContextScopes.REQUEST, strict_scope=True
    )
    g = providers.ContextResource(_g_resource, c=c, d=d, e=e, f=f).with_config(
        scope=ContextScopes.REQUEST, strict_scope=True
    )

    h = providers.ContextResource(services.make_h, c=c, d=d).with_config(scope=ContextScopes.REQUEST, strict_scope=True)
    i = providers.ContextResource(services.make_i, e=e, f=f).with_config(scope=ContextScopes.REQUEST, strict_scope=True)


router = APIRouter(prefix="/that_depends", tags=["that-depends"])


@router.get("/singleton")
async def get_singleton(
    a: Annotated[services.A, Depends(Container.a)],
    b: Annotated[services.B, Depends(Container.b)],
):
    services.record_request("singleton")
    assert a.start == 10
    assert isinstance(a, services.A)
    assert isinstance(b, services.B)
    return {}


@router.get("/scoped")
async def get_scoped(
    c: Annotated[services.C, Depends(Container.c)],
    cc: Annotated[services.C, Depends(Container.c)],
    ccc: Annotated[services.C, Depends(Container.c)],
    d: Annotated[services.D, Depends(Container.d)],
    dd: Annotated[services.D, Depends(Container.d)],
    e: Annotated[services.E, Depends(Container.e)],
    f: Annotated[services.F, Depends(Container.f)],
    g: Annotated[services.G, Depends(Container.g)],
    h: Annotated[services.H, Depends(Container.h)],
    i: Annotated[services.I, Depends(Container.i)],
):
    services.record_request("scoped")
    assert isinstance(c, services.C)
    assert c is cc
    assert cc is ccc

    assert isinstance(d, services.D)
    assert isinstance(e, services.E)
    assert isinstance(f, services.F)
    assert isinstance(g, services.G)
    assert isinstance(h, services.H)
    assert isinstance(i, services.I)
    assert d is dd
    return {}
