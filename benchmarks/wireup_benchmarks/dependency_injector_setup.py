from dataclasses import dataclass
from typing import Any, Dict

import fastapi
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from typing_extensions import Annotated


@dataclass(frozen=True)
class A:
    start: int


@dataclass(frozen=True)
class B:
    a: A


@dataclass(frozen=True)
class C:
    a: A
    b: B


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=["wireup_benchmarks.dependency_injector_setup"])
    config = providers.Configuration()

    a = providers.Factory(A, start=10)
    b = providers.Factory(B, a=a)
    c = providers.Factory(C, b=b, a=a)


router = fastapi.APIRouter()


@router.get("/dependency_injector/singleton")
@inject
def dependency_injector_singleton(
    a: Annotated[A, Depends(Provide[Container.a])],
    b: Annotated[A, Depends(Provide[Container.b])],
) -> Dict[str, Any]:
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/dependency_injector/scoped")
@inject
def dependency_injector_scoped() -> Dict[str, Any]:
    raise Exception("Dependency Injector does not support scopes")


container = Container()
container.config.from_dict({"start": 10})
container.wire(modules=[__name__])
