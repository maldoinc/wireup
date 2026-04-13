from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Set

import wireup
from wireup import Injected, injectable


class Cache(ABC):
    @abstractmethod
    def name(self) -> str: ...


@injectable(as_type=Cache, qualifier="redis")
class RedisCache(Cache):
    def name(self) -> str:
        return "redis"


@injectable(as_type=Cache, qualifier="in_memory")
class InMemoryCache(Cache):
    def name(self) -> str:
        return "in_memory"


@injectable
class CacheConsumer:
    def __init__(self, caches: Injected[Set[Cache]]) -> None:
        self.caches = caches


def test_set_of_qualified_cache_impls_is_injected() -> None:
    container = wireup.create_sync_container(
        injectables=[RedisCache, InMemoryCache, CacheConsumer],
    )
    consumer = container.get(CacheConsumer)

    assert len(consumer.caches) == 2
    names = {cache.name() for cache in consumer.caches}
    assert names == {"redis", "in_memory"}
