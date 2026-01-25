from __future__ import annotations

import asyncio
import threading
from typing import Dict


class LockRegistry(Dict[int, "asyncio.Lock | threading.Lock"]):
    __slots__ = ("_async_hashes", "_lock")

    def __init__(self, async_hashes: set[int]) -> None:
        super().__init__()
        self._async_hashes = async_hashes
        self._lock = threading.Lock()

    def __missing__(self, key: int) -> asyncio.Lock | threading.Lock:
        with self._lock:
            if key not in self:
                self[key] = asyncio.Lock() if key in self._async_hashes else threading.Lock()
            return self[key]
