import re
from typing import AsyncIterator, Iterator, NewType

import pytest
import wireup
from wireup._decorators import inject_from_container
from wireup.errors import ContainerCloseError, WireupError

from test.conftest import Container
from test.unit.util import run


async def test_cleans_up_on_exit(container: Container) -> None:
    _cleanup_performed = False
    Something = NewType("Something", str)

    def some_factory() -> Iterator[Something]:
        yield Something("foo")
        nonlocal _cleanup_performed
        _cleanup_performed = True

    container._registry.register(some_factory)

    assert await run(container.get(Something)) == Something("foo")
    await run(container.close())
    assert _cleanup_performed


async def test_async_cleans_up_on_exit() -> None:
    _cleanup_performed = False
    Something = NewType("Something", str)

    async def some_factory() -> AsyncIterator[Something]:
        yield Something("foo")
        nonlocal _cleanup_performed
        _cleanup_performed = True

    container = wireup.create_async_container()
    container._registry.register(some_factory)

    @inject_from_container(container)
    async def target(smth: Something):
        assert smth == Something("foo")

    await target()
    await container.close()
    assert _cleanup_performed


def test_injects_transient() -> None:
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

    container = wireup.create_sync_container()
    container._registry.register(f1, lifetime="transient")
    container._registry.register(f2, lifetime="transient")

    @inject_from_container(container, lambda: scoped)
    def target(_: SomethingElse) -> None:
        pass

    with container.enter_scope() as scoped:
        target()

    assert _cleanups == ["f2", "f1"]


async def test_async_injects_transient_sync_depends_on_async_result() -> None:
    _cleanups: list[str] = []
    Something = NewType("Something", str)
    SomethingElse = NewType("SomethingElse", str)

    async def f1() -> AsyncIterator[Something]:
        yield Something("Something")
        nonlocal _cleanups
        _cleanups.append("f1")

    def f2(something: Something) -> Iterator[SomethingElse]:
        yield SomethingElse(f"{something} else")
        nonlocal _cleanups
        _cleanups.append("f2")

    container = wireup.create_async_container()
    container._registry.register(f1, lifetime="transient")
    container._registry.register(f2, lifetime="transient")

    async with container.enter_scope() as scoped:
        await scoped.get(SomethingElse)
    assert _cleanups == ["f2", "f1"]


async def test_cleans_up_in_order(container: Container) -> None:
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

    container._registry.register(f1)
    container._registry.register(f2)

    assert await run(container.get(Something)) == Something("Something")
    assert await run(container.get(SomethingElse)) == SomethingElse("Something else")
    await run(container.close())
    assert _cleanups == ["f2", "f1"]


def test_sync_raises_when_generating_async() -> None:
    Something = NewType("Something", str)

    async def f1() -> AsyncIterator[Something]:
        yield Something("Something")
        raise ValueError("boom")

    c = wireup.create_sync_container()
    c._registry.register(f1)

    @inject_from_container(c)
    def target(_: Something) -> None:
        pass

    with pytest.raises(
        WireupError,
        match=re.escape(
            f"{Something} is an async dependency and it cannot be created in a synchronous context. "
            "Create and use an async container via wireup.create_async_container. "
        ),
    ):
        target()


def test_raises_errors() -> None:
    Something = NewType("Something", str)

    def f1() -> Iterator[Something]:
        yield Something("Something")
        raise ValueError("boom")

    c = wireup.create_sync_container()
    c._registry.register(f1)

    assert c.get(Something) == Something("Something")
    with pytest.raises(ContainerCloseError) as e:
        c.close()

    assert len(e.value.errors) == 1
    assert isinstance(e.value.errors[0], ValueError)
    assert str(e.value.errors[0]) == "boom"
