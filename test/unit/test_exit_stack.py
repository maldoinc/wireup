import asyncio
import re
from collections.abc import AsyncGenerator, Generator

import pytest
from wireup.errors import WireupError
from wireup.ioc._exit_stack import async_clean_exit_stack, clean_exit_stack


class _Cancelled(BaseException):
    """Stand-in for a BaseException (not Exception) re-raised during teardown.

    Mirrors asyncio.CancelledError / KeyboardInterrupt / SystemExit without
    tripping pytest's session-level handling of the latter two.
    """


def test_clean_exit_stack_with_sync_generators() -> None:
    g1_done = False
    g2_done = False

    def gen_1() -> Generator[None, None, None]:
        yield
        nonlocal g1_done
        g1_done = True

    def gen_2() -> Generator[None, None, None]:
        yield
        nonlocal g2_done
        g2_done = True

    g1 = gen_1()
    next(g1)
    g2 = gen_2()
    next(g2)

    clean_exit_stack([(g1, False), (g2, False)])
    assert g1_done
    assert g2_done


async def test_clean_exit_stack_with_async_generators_raises() -> None:
    async def gen_1() -> AsyncGenerator[None, None]:
        yield

    g1 = gen_1()
    await g1.__anext__()

    with pytest.raises(
        WireupError,
        match=re.escape(
            "The following generators are async factories and closing them with a SyncContainer is not possible. "
            "If you require async dependencies create an AsyncContainer via wireup.create_async_container instead. "
            f"List of async factories encountered: {[g1]}."
        ),
    ):
        clean_exit_stack([(g1, True)])


def test_clean_exit_stack_continues_teardown_when_unwinding_base_exception() -> None:
    # KeyboardInterrupt / SystemExit are BaseException, not Exception. When one is
    # being unwound, every generator must still be torn down and the stack cleared.
    teardowns: list[str] = []

    def make(name: str) -> Generator[None, None, None]:
        try:
            yield
        finally:
            teardowns.append(name)

    g1 = make("first")
    next(g1)
    g2 = make("second")
    next(g2)

    exit_stack = [(g1, False), (g2, False)]
    clean_exit_stack(exit_stack, exc_val=_Cancelled())

    assert teardowns == ["second", "first"]
    assert exit_stack == []


async def test_async_clean_exit_stack_continues_teardown_on_cancellation() -> None:
    # Regression: when an `async with container.enter_scope()` block is cancelled
    # (asyncio.wait_for timeout, task.cancel()), the CancelledError is re-raised by
    # each generator's teardown. Cleanup must not abort early and leak the rest.
    teardowns: list[str] = []

    async def make(name: str) -> AsyncGenerator[None, None]:
        try:
            yield
        finally:
            teardowns.append(name)

    g1 = make("first")
    await g1.__anext__()
    g2 = make("second")
    await g2.__anext__()

    exit_stack = [(g1, True), (g2, True)]
    await async_clean_exit_stack(exit_stack, exc_val=asyncio.CancelledError())

    assert teardowns == ["second", "first"]
    assert exit_stack == []


async def test_async_clean_exit_stack_propagates_new_base_exception_from_teardown() -> None:
    # A brand-new BaseException raised during teardown (not the one being unwound)
    # must still propagate rather than be silently swallowed.
    async def gen() -> AsyncGenerator[None, None]:
        try:
            yield
        finally:
            raise KeyboardInterrupt

    g = gen()
    await g.__anext__()

    with pytest.raises(KeyboardInterrupt):
        await async_clean_exit_stack([(g, True)])
