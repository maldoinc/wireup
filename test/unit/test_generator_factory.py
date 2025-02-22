import re
from typing import AsyncIterator, Iterator, NewType

import pytest
import wireup
from wireup.decorators import make_inject_decorator
from wireup.errors import ContainerCloseError, WireupError
from wireup.ioc.types import ServiceLifetime


def test_cleans_up_on_exit() -> None:
    _cleanup_performed = False
    Something = NewType("Something", str)

    def some_factory() -> Iterator[Something]:
        yield Something("foo")
        nonlocal _cleanup_performed
        _cleanup_performed = True

    c = wireup.create_sync_container()
    c._registry.register_factory(some_factory)

    assert c.get(Something) == Something("foo")
    c.close()
    assert _cleanup_performed


async def test_async_cleans_up_on_exit() -> None:
    _cleanup_performed = False
    Something = NewType("Something", str)

    async def some_factory() -> AsyncIterator[Something]:
        yield Something("foo")
        nonlocal _cleanup_performed
        _cleanup_performed = True

    c = wireup.create_async_container()
    c._registry.register_factory(some_factory)

    @make_inject_decorator(c)
    async def target(smth: Something):
        assert smth == Something("foo")

    await target()
    await c.close()
    assert _cleanup_performed


async def test_async_raise_close_async() -> None:
    Something = NewType("Something", str)

    async def some_factory() -> AsyncIterator[Something]:
        yield Something("foo")

    c = wireup.create_sync_container()
    c._registry.register_factory(some_factory)

    @make_inject_decorator(c)
    async def target(smth: Something):
        assert smth == Something("foo")

    await target()
    msg = re.escape(
        "The following generators are async factories and closing the container with `container.close()`"
        " is not possible. Replace the `container.close()` call with `await container.aclose()`. "
        "If you used `wireup.enter_scope`, you should use `wireup.enter_async_scope` instead. "
        "List of async factories:"
    )
    with pytest.raises(WireupError, match=msg):
        c.close()


def test_raises_on_transient_dependency() -> None:
    Something = NewType("Something", str)

    def some_factory() -> Iterator[Something]:
        yield Something("foo")

    c = wireup.create_sync_container()
    c._registry.register_factory(some_factory, lifetime=ServiceLifetime.TRANSIENT)

    with pytest.raises(WireupError) as e:
        c.get(Something)

    assert str(e.value) == "Container.get does not support Transient lifetime service generator factories."


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

    c = wireup.create_sync_container()
    c._registry.register_factory(f1, lifetime=ServiceLifetime.TRANSIENT)
    c._registry.register_factory(f2, lifetime=ServiceLifetime.TRANSIENT)

    @make_inject_decorator(c)
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

    c = wireup.create_sync_container()
    c._registry.register_factory(f1, lifetime=ServiceLifetime.TRANSIENT)
    c._registry.register_factory(f2, lifetime=ServiceLifetime.TRANSIENT)

    @make_inject_decorator(c)
    async def target(_: SomethingElse) -> None:
        pass

    await target()
    assert _cleanups == ["f2", "f1"]


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

    c = wireup.create_sync_container()
    c._registry.register_factory(f1)
    c._registry.register_factory(f2)

    assert c.get(Something) == Something("Something")
    assert c.get(SomethingElse) == SomethingElse("Something else")
    c.close()
    assert _cleanups == ["f2", "f1"]


def test_sync_raises_when_generating_async() -> None:
    Something = NewType("Something", str)

    async def f1() -> AsyncIterator[Something]:
        yield Something("Something")
        raise ValueError("boom")

    c = wireup.create_sync_container()
    c._registry.register_factory(f1)

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
    c._registry.register_factory(f1)

    assert c.get(Something) == Something("Something")
    with pytest.raises(ContainerCloseError) as e:
        c.close()

    assert len(e.value.errors) == 1
    assert isinstance(e.value.errors[0], ValueError)
    assert str(e.value.errors[0]) == "boom"
