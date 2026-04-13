from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from typing import Set

import wireup
from wireup import Injected, injectable
from wireup.ioc.types import CollectionInjectionRequest
from wireup.ioc.util import param_get_annotation


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


def test_param_get_annotation_detects_set_of_interface() -> None:
    def target(caches: Set[Cache]) -> None: ...

    parameter = inspect.signature(target).parameters["caches"]
    result = param_get_annotation(parameter, globalns_supplier=lambda: globals())

    assert result is not None
    assert result.klass is Cache
    assert isinstance(result.annotation, CollectionInjectionRequest)
    assert result.annotation.collection_type is set
    assert result.annotation.inner_type is Cache


def test_param_get_annotation_detects_injected_set_of_interface() -> None:
    def target(caches: Injected[Set[Cache]]) -> None: ...

    parameter = inspect.signature(target).parameters["caches"]
    result = param_get_annotation(parameter, globalns_supplier=lambda: globals())

    assert result is not None
    assert result.klass is Cache
    assert isinstance(result.annotation, CollectionInjectionRequest)
    assert result.annotation.inner_type is Cache


def test_set_of_qualified_cache_impls_is_injected() -> None:
    container = wireup.create_sync_container(
        injectables=[RedisCache, InMemoryCache, CacheConsumer],
    )
    consumer = container.get(CacheConsumer)

    assert len(consumer.caches) == 2
    names = {cache.name() for cache in consumer.caches}
    assert names == {"redis", "in_memory"}
