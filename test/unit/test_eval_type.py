from __future__ import annotations

import importlib
from collections.abc import Iterator  # noqa: TC003
from dataclasses import dataclass

import wireup
from typing_extensions import Annotated
from wireup._decorators import inject_from_container


@wireup.service
class A: ...


@wireup.service
@dataclass
class B:
    a: A
    aa: A


@dataclass
class C:
    b: B


@wireup.service
def c_factory(b: B) -> Iterator[C]:
    yield C(b)


def test_eval_type_evaluates_strings() -> None:
    container = wireup.create_sync_container(
        parameters={"foo": "bar"}, service_modules=[importlib.import_module(__name__)]
    )

    @inject_from_container(container)
    def test(a: A, b: B, c: C, foo: Annotated[str, wireup.Inject(param="foo")], _: int = 1):
        assert isinstance(a, A)
        assert isinstance(b, B)
        assert isinstance(c, C)
        assert foo == "bar"

    test()

    assert isinstance(container.get(A), A)
    assert isinstance(container.get(B), B)
    assert isinstance(container.get(C), C)
