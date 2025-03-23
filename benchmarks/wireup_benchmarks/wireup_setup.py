from dataclasses import dataclass
from typing import Dict

import fastapi
from typing_extensions import Annotated
from wireup import Inject, Injected, service
from wireup.integration.fastapi import WireupRoute


@service
@dataclass(frozen=True)
class A:
    start: Annotated[int, Inject(param="start")]


@service
@dataclass(frozen=True)
class B:
    a: A


@service(lifetime="scoped")
@dataclass(frozen=True)
class C:
    a: A
    b: B


router = fastapi.APIRouter(route_class=WireupRoute)


@router.get("/wireup/singleton")
def wireup_singleton(a: Injected[A], b: Injected[B]) -> Dict[str, str]:
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/wireup/scoped")
def wireup_scoped(a: Injected[A], c: Injected[C], cc: Injected[C], ccc: Injected[C]) -> Dict[str, str]:
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(c, C)
    assert c is cc
    assert cc is ccc
    return {}
