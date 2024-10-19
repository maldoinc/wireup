from collections.abc import Iterator
from typing import NewType

import pytest
from wireup import DependencyContainer, ParameterBag
from wireup.errors import ContainerCloseError, WireupError
from wireup.ioc.types import ServiceLifetime


def test_cleans_up_on_exit() -> None:
    _cleanup_performed = False
    Something = NewType("Something", str)

    def some_factory() -> Iterator[Something]:
        yield Something("foo")
        nonlocal _cleanup_performed
        _cleanup_performed = True

    c = DependencyContainer(ParameterBag())
    c.register(some_factory)

    assert c.get(Something) == Something("foo")
    c.close()
    assert _cleanup_performed


def test_raises_on_transient_dependency() -> None:
    Something = NewType("Something", str)

    def some_factory() -> Iterator[Something]:
        yield Something("foo")

    c = DependencyContainer(ParameterBag())
    c.register(some_factory, lifetime=ServiceLifetime.TRANSIENT)

    with pytest.raises(WireupError) as e:
        c.get(Something)

    assert str(e.value) == "Generators are not currently supported with transient-scoped dependencies."


def test_cleans_up_in_order() -> None:
    _cleanups: list[str] = []
    Something = NewType("Something", str)
    SomethingElse = NewType("SomethingElse", str)

    def f1() -> Iterator[Something]:
        yield Something("Something")
        nonlocal _cleanups
        _cleanups.append("f1")

    def f2(something: Something) -> Iterator[SomethingElse]:
        yield SomethingElse(f"{something} else")
        nonlocal _cleanups
        _cleanups.append("f2")

    c = DependencyContainer(ParameterBag())
    c.register(f1)
    c.register(f2)

    assert c.get(Something) == Something("Something")
    assert c.get(SomethingElse) == SomethingElse("Something else")
    c.close()
    assert _cleanups == ["f2", "f1"]


def test_raises_errors() -> None:
    Something = NewType("Something", str)

    def f1() -> Iterator[Something]:
        yield Something("Something")
        raise ValueError("boom")

    c = DependencyContainer(ParameterBag())
    c.register(f1)

    assert c.get(Something) == Something("Something")
    with pytest.raises(ContainerCloseError) as e:
        c.close()

    assert len(e.value.errors) == 1
    assert isinstance(e.value.errors[0], ValueError)
    assert str(e.value.errors[0]) == "boom"
