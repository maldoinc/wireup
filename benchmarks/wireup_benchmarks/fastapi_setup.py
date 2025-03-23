from dataclasses import dataclass
from functools import lru_cache
from typing import Dict

import fastapi
from typing_extensions import Annotated


class Settings:
    start: int = 10


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


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_a(settings: Annotated[Settings, fastapi.Depends(get_settings)]) -> A:
    return A(start=settings.start)


@lru_cache
def get_b(a: Annotated[A, fastapi.Depends(get_a)]) -> B:
    return B(a)


def get_c(a: Annotated[A, fastapi.Depends(get_a)], b: Annotated[B, fastapi.Depends(get_b)]) -> C:
    return C(a=a, b=b)


router = fastapi.APIRouter()


@router.get("/fastapi/singleton")
def fastapi_singleton(
    a: Annotated[A, fastapi.Depends(get_a)], b: Annotated[B, fastapi.Depends(get_b)]
) -> Dict[str, str]:
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(b, B)
    return {}


@router.get("/fastapi/scoped")
def fastapi_scoped(
    a: Annotated[A, fastapi.Depends(get_a)],
    c: Annotated[C, fastapi.Depends(get_c)],
    cc: Annotated[C, fastapi.Depends(get_c)],
    ccc: Annotated[C, fastapi.Depends(get_c)],
) -> Dict[str, str]:
    assert a.start == 10
    assert isinstance(a, A)
    assert isinstance(c, C)
    assert c is cc
    assert cc is ccc
    return {}
