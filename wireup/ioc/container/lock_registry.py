from __future__ import annotations

import asyncio
import threading


class LockRegistry:
    __slots__ = ("_global_lock", "_scoped_locks")

    def __init__(self) -> None:
        self._global_lock = threading.Lock()
        self._scoped_locks: dict[object, asyncio.Lock | threading.Lock] = {}

    def get_lock(self, key: object, *, needs_async_lock: bool) -> asyncio.Lock | threading.Lock:
        with self._global_lock:
            if key not in self._scoped_locks:
                self._scoped_locks[key] = asyncio.Lock() if needs_async_lock else threading.Lock()

            return self._scoped_locks[key]
