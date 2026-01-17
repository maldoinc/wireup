import re
from typing import AsyncIterator, Iterator, NewType

import pytest
import wireup
from wireup import Injected, inject_from_container
from wireup._annotations import injectable
from wireup.errors import ContainerCloseError, WireupError

from test.conftest import Container
from test.unit.util import run


def test_cleans_up_on_exit(container: Container) -> None:
    _cleanup_performed = False
    Something = NewType("Something", str)

    @injectable
    def some_factory() -> Iterator[Something]:
        yield Something("foo")
        nonlocal _cleanup_performed
        _cleanup_performed = True

    container = wireup.create_sync_container(injectables=[some_factory])

    assert container.get(Something) == Something("foo")
    container.close()
    assert _cleanup_performed


async def test_async_cleans_up_on_exit() -> None:
    _cleanup_performed = False
    Something = NewType("Something", str)

    @injectable
    async def some_factory() -> AsyncIterator[Something]:
        yield Something("foo")
        nonlocal _cleanup_performed
        _cleanup_performed = True

    container = wireup.create_async_container(injectables=[some_factory])

    @inject_from_container(container)
    async def target(smth: Injected[Something]):
        assert smth == Something("foo")

    await target()
    await container.close()
    assert _cleanup_performed


def test_injects_transient() -> None:
    _cleanups: list[str] = []
    Something = NewType("Something", str)
    SomethingElse = NewType("SomethingElse", str)

    @injectable(lifetime="transient")
    def f1() -> Iterator[Something]:
        yield Something("Something")
        nonlocal _cleanups
        _cleanups.append("f1")

    @injectable(lifetime="transient")
    def f2(something: Something) -> Iterator[SomethingElse]:
        yield SomethingElse(f"{something} else")
        nonlocal _cleanups
        _cleanups.append("f2")

    container = wireup.create_sync_container(injectables=[f1, f2])

    @inject_from_container(container, lambda: scoped)
    def target(_: Injected[SomethingElse]) -> None:
        pass

    with container.enter_scope() as scoped:
        target()

    assert _cleanups == ["f2", "f1"]


async def test_async_injects_transient_sync_depends_on_async_result() -> None:
    _cleanups: list[str] = []
    Something = NewType("Something", str)
    SomethingElse = NewType("SomethingElse", str)

    @injectable(lifetime="transient")
    async def f1() -> AsyncIterator[Something]:
        yield Something("Something")
        nonlocal _cleanups
        _cleanups.append("f1")

    @injectable(lifetime="transient")
    def f2(something: Something) -> Iterator[SomethingElse]:
        yield SomethingElse(f"{something} else")
        nonlocal _cleanups
        _cleanups.append("f2")

    container = wireup.create_async_container(injectables=[f1, f2])

    async with container.enter_scope() as scoped:
        await scoped.get(SomethingElse)
    assert _cleanups == ["f2", "f1"]


def test_cleans_up_in_order() -> None:
    _cleanups: list[str] = []
    Something = NewType("Something", str)
    SomethingElse = NewType("SomethingElse", str)

    @injectable
    def f1() -> Iterator[Something]:
        yield Something("Something")
        nonlocal _cleanups
        _cleanups.append("f1")

    @injectable
    def f2(something: Something) -> Iterator[SomethingElse]:
        yield SomethingElse(f"{something} else")
        nonlocal _cleanups
        _cleanups.append("f2")

    container = wireup.create_sync_container(injectables=[f1, f2])

    assert container.get(Something) == Something("Something")
    assert container.get(SomethingElse) == SomethingElse("Something else")
    container.close()
    assert _cleanups == ["f2", "f1"]


def test_sync_raises_when_generating_async() -> None:
    Something = NewType("Something", str)

    @injectable
    async def f1() -> AsyncIterator[Something]:
        yield Something("Something")
        raise ValueError("boom")

    c = wireup.create_sync_container(injectables=[f1])

    @inject_from_container(c)
    def target(_: Injected[Something]) -> None:
        pass

    with pytest.raises(
        WireupError,
        match=re.escape(
            "is an async dependency and it cannot be created in a synchronous context. "
            "Create and use an async container via wireup.create_async_container."
        ),
    ):
        target()


def test_raises_errors() -> None:
    Something = NewType("Something", str)

    @injectable
    def f1() -> Iterator[Something]:
        yield Something("Something")
        raise ValueError("boom")

    c = wireup.create_sync_container(injectables=[f1])

    assert c.get(Something) == Something("Something")
    with pytest.raises(ContainerCloseError) as e:
        c.close()

    assert len(e.value.errors) == 1
    assert isinstance(e.value.errors[0], ValueError)
    assert str(e.value.errors[0]) == "boom"


async def test_raises_errors_async() -> None:
    Something = NewType("Something", str)

    @injectable
    async def f1() -> AsyncIterator[Something]:
        yield Something("Something")
        raise ValueError("boom")

    c = wireup.create_async_container(injectables=[f1])

    assert await c.get(Something) == Something("Something")
    with pytest.raises(ContainerCloseError) as e:
        await c.close()

    assert len(e.value.errors) == 1
    assert isinstance(e.value.errors[0], ValueError)
    assert str(e.value.errors[0]) == "boom"


def test_sync_container_clears_exit_stack_on_close() -> None:
    Something = NewType("Something", str)

    @injectable
    def my_gen() -> Iterator[Something]:
        yield Something("start")

    container = wireup.create_sync_container(injectables=[my_gen])
    container.get(Something)
    assert len(container._global_scope_exit_stack) == 1

    container.close()
    assert len(container._global_scope_exit_stack) == 0

    container.close()


async def test_async_container_clears_exit_stack_on_close() -> None:
    Something = NewType("Something", str)

    @injectable
    async def my_gen() -> AsyncIterator[Something]:
        yield Something("start")

    container = wireup.create_async_container(injectables=[my_gen])

    @inject_from_container(container)
    async def target(val: Injected[Something]) -> None:
        pass

    await target()
    assert len(container._global_scope_exit_stack) == 1
    await container.close()
    assert len(container._global_scope_exit_stack) == 0
    await container.close()
