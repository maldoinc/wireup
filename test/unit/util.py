from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Coroutine

T = TypeVar("T")


async def run(source: T | Coroutine[None, None, T]) -> T:
    return await source if asyncio.iscoroutine(source) else source  # type:ignore[Any]
