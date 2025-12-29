from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator  # noqa: TC003
from dataclasses import dataclass

import pytest
import wireup
from typing_extensions import Annotated
from wireup import Injected, inject_from_container


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
    container = wireup.create_sync_container(config={"foo": "bar"}, service_modules=[importlib.import_module(__name__)])

    @inject_from_container(container)
    def test(
        a: Injected[A], b: Injected[B], c: Injected[C], foo: Annotated[str, wireup.Inject(config="foo")], _: int = 1
    ):
        assert isinstance(a, A)
        assert isinstance(b, B)
        assert isinstance(c, C)
        assert foo == "bar"

    test()

    assert isinstance(container.get(A), A)
    assert isinstance(container.get(B), B)
    assert isinstance(container.get(C), C)


@pytest.mark.skipif(sys.version_info < (3, 11), reason="eval_type_backport only needed for Python < 3.11")
def test_eval_type_backport_not_imported_on_py311_and_newer() -> None:
    container = wireup.create_sync_container(service_modules=[importlib.import_module(__name__)])

    container.get(A)
    container.get(B)

    # On Python 3.11+, eval_type_backport should not be imported since the native typing._eval_type should suffice.
    assert "eval_type_backport" not in sys.modules
