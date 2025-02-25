import re
from typing import AsyncIterator, Iterator, NewType

import pytest
import wireup
from wireup.decorators import make_inject_decorator
from wireup.errors import ContainerCloseError, WireupError
from wireup.ioc.types import ServiceLifetime

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

    @make_inject_decorator(container)
    async def target(smth: Something):
        assert smth == Something("foo")

    await target()
    await container.close()
    assert _cleanup_performed


async def test_async_raise_close_async() -> None:
    Something = NewType("Something", str)

    async def some_factory() -> AsyncIterator[Something]:
        yield Something("foo")

    container = wireup.create_sync_container()
    container._registry.register(some_factory)

    @make_inject_decorator(container)
    async def target(smth: Something):
        assert smth == Something("foo")

    await target()
    msg = (
        "The following generators are async factories and closing them with a SyncContainer is not possible. "
        "If you require async dependencies create an AsyncContainer via wireup.create_async_container instead."
        "List of async factories:"
    )
    with pytest.raises(WireupError, match=msg):
        container.close()


async def test_raises_on_transient_dependency(container: Container) -> None:
    Something = NewType("Something", str)

    def some_factory() -> Iterator[Something]:
        yield Something("foo")

    container._registry.register(some_factory, lifetime=ServiceLifetime.TRANSIENT)

    with pytest.raises(
        WireupError, match="Container.get does not support Transient lifetime service generator factories."
    ):
        await run(container.get(Something))


def test_injects_transient(container: Container) -> None:
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

    container._registry.register(f1, lifetime=ServiceLifetime.TRANSIENT)
    container._registry.register(f2, lifetime=ServiceLifetime.TRANSIENT)

    @make_inject_decorator(container)
    def target(_: SomethingElse) -> None:
        pass

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
    container._registry.register(f1, lifetime=ServiceLifetime.TRANSIENT)
    container._registry.register(f2, lifetime=ServiceLifetime.TRANSIENT)

    async with wireup.enter_async_scope(container) as scoped:
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

    @make_inject_decorator(c)
    def target(_: Something) -> None:
        pass

    with pytest.raises(
        WireupError,
        match=re.escape(
            f"{Something} is an async dependency and it cannot be created in a blocking context. "
            f"You likely used `container.get({Something.__module__}.{Something.__name__})` or called `get` on a dependent. "  # noqa: E501
            "Use `await container.aget` instead of `container.get`."
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
