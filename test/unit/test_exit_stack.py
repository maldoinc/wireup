import re
from typing import AsyncGenerator, Generator

import pytest
from wireup.errors import WireupError
from wireup.ioc._exit_stack import clean_exit_stack


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
