from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator  # noqa: TC003
from dataclasses import dataclass
from typing import Annotated, get_args

import pytest
import wireup
from wireup import Injected, inject_from_container
from wireup.ioc.util import ensure_is_type


@wireup.injectable
class A: ...


@wireup.injectable
@dataclass
class B:
    a: A
    aa: A


@dataclass
class C:
    b: B


@wireup.injectable
def c_factory(b: B) -> Iterator[C]:
    yield C(b)


def test_eval_type_evaluates_strings() -> None:
    container = wireup.create_sync_container(config={"foo": "bar"}, injectables=[importlib.import_module(__name__)])

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


def test_eval_type_resolves_cached_forward_references_in_each_namespace() -> None:
    for dependency in (A, B, A):
        namespace = {"Injected": Injected, "Dependency": dependency}
        resolved = ensure_is_type("Injected['Dependency']", globalns_supplier=lambda namespace=namespace: namespace)
        assert get_args(resolved)[0] is dependency


@pytest.mark.skipif(sys.version_info < (3, 11), reason="eval_type_backport only needed for Python < 3.11")
def test_eval_type_backport_not_imported_on_py311_and_newer() -> None:
    container = wireup.create_sync_container(injectables=[importlib.import_module(__name__)])

    container.get(A)
    container.get(B)
    with pytest.raises(TypeError):
        ensure_is_type("int + str", globalns_supplier=dict)

    # On Python 3.11+, eval_type_backport should not be imported since native
    # typing._eval_type either resolves the annotation or reports its error.
    assert "eval_type_backport" not in sys.modules
