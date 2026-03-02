from typing import Any, Dict

import fastapi
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from typing_extensions import Annotated

from wireup_benchmarks import services


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=["wireup_benchmarks.dependency_injector_setup"])
    config = providers.Configuration()

    settings = providers.Singleton(services.Settings, start=config.start)
    a = providers.Singleton(services.make_a, settings=settings)
    b = providers.Singleton(services.B, a=a)
    c = providers.ContextLocalSingleton(services.C)
    d = providers.ContextLocalSingleton(services.D, c=c)
    e = providers.ContextLocalSingleton(services.E, c=c, d=d)
    f = providers.ContextLocalSingleton(services.F, c=c, d=d, e=e)
    g = providers.ContextLocalSingleton(services.G, c=c, d=d, e=e, f=f)
    # Context-local singletons to match per-request scoping without resource lifecycle.
    h = providers.ContextLocalSingleton(services.H, c=c, d=d)
    i = providers.ContextLocalSingleton(services.I, e=e, f=f)


router = fastapi.APIRouter()


@router.get("/dependency_injector/singleton")
@inject
async def dependency_injector_singleton(
    a: Annotated[services.A, Depends(Provide[Container.a])],
    b: Annotated[services.B, Depends(Provide[Container.b])],
) -> Dict[str, Any]:
    services.record_request("singleton")
    assert a.start == 10
    assert isinstance(a, services.A)
    assert isinstance(b, services.B)
    return {}


@router.get("/dependency_injector/scoped")
@inject
async def dependency_injector_scoped(
    c: Annotated[services.C, Depends(Provide[Container.c])],
    cc: Annotated[services.C, Depends(Provide[Container.c])],
    ccc: Annotated[services.C, Depends(Provide[Container.c])],
    d: Annotated[services.D, Depends(Provide[Container.d])],
    dd: Annotated[services.D, Depends(Provide[Container.d])],
    e: Annotated[services.E, Depends(Provide[Container.e])],
    f: Annotated[services.F, Depends(Provide[Container.f])],
    g: Annotated[services.G, Depends(Provide[Container.g])],
    h: Annotated[services.H, Depends(Provide[Container.h])],
    i: Annotated[services.I, Depends(Provide[Container.i])],
) -> Dict[str, Any]:
    services.record_request("scoped")
    assert isinstance(c, services.C)
    assert c is cc
    assert cc is ccc

    assert isinstance(d, services.D)
    assert d is dd

    assert isinstance(e, services.E)
    assert isinstance(f, services.F)
    assert isinstance(g, services.G)
    assert isinstance(h, services.H)
    assert isinstance(i, services.I)

    return {}


container = Container()
container.config.from_dict({"start": 10})
container.wire(modules=[__name__])
