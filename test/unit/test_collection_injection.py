from __future__ import annotations

import inspect
import re
from abc import ABC, abstractmethod
from typing import Set

import pytest

import wireup
from wireup import Injected, injectable
from wireup.errors import CollectionInterfaceUnknownError, WireupError
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


# ---- Validation rules ----

class _UnknownInterface(ABC):
    @abstractmethod
    def name(self) -> str: ...


def test_collection_of_unknown_type_raises_collection_interface_unknown_error() -> None:
    @injectable
    class UnknownConsumer:
        def __init__(self, impls: Injected[Set[_UnknownInterface]]) -> None:
            self.impls = impls

    with pytest.raises(
        CollectionInterfaceUnknownError,
        match=re.escape("_UnknownInterface"),
    ):
        wireup.create_sync_container(injectables=[UnknownConsumer])


class _ScopedCache(ABC):
    @abstractmethod
    def name(self) -> str: ...


@injectable(as_type=_ScopedCache, qualifier="scoped_one", lifetime="scoped")
class _ScopedCacheImplA(_ScopedCache):
    def name(self) -> str:
        return "scoped_one"


@injectable(as_type=_ScopedCache, qualifier="scoped_two", lifetime="scoped")
class _ScopedCacheImplB(_ScopedCache):
    def name(self) -> str:
        return "scoped_two"


@injectable  # default lifetime is singleton
class _SingletonConsumerOfScopedCollection:
    def __init__(self, caches: Injected[Set[_ScopedCache]]) -> None:
        self.caches = caches


def test_singleton_consumer_of_non_singleton_collection_is_rejected() -> None:
    with pytest.raises(
        WireupError,
        match=re.escape("Singletons can only depend on other singletons"),
    ):
        wireup.create_sync_container(
            injectables=[
                _ScopedCacheImplA,
                _ScopedCacheImplB,
                _SingletonConsumerOfScopedCollection,
            ],
        )


class _CycleInterface(ABC):
    @abstractmethod
    def tag(self) -> str: ...


@injectable(as_type=_CycleInterface, qualifier="cycle_a")
class _CycleImplA(_CycleInterface):
    def __init__(self, consumer: _CycleConsumer) -> None:  # type: ignore[name-defined]  # noqa: F821
        self.consumer = consumer

    def tag(self) -> str:
        return "a"


@injectable
class _CycleConsumer:
    def __init__(self, impls: Injected[Set[_CycleInterface]]) -> None:
        self.impls = impls


def test_cycle_through_collection_dep_is_rejected() -> None:
    with pytest.raises(WireupError, match=re.escape("Circular dependency")):
        wireup.create_sync_container(injectables=[_CycleImplA, _CycleConsumer])


# ---- Async variant ----

class _AsyncCache(ABC):
    @abstractmethod
    def tag(self) -> str: ...


class _AsyncRedisCache(_AsyncCache):
    def tag(self) -> str:
        return "async_redis"


class _AsyncMemoryCache(_AsyncCache):
    def tag(self) -> str:
        return "async_memory"


@injectable(as_type=_AsyncCache, qualifier="async_redis")
async def _async_redis_factory() -> _AsyncRedisCache:
    return _AsyncRedisCache()


@injectable(as_type=_AsyncCache, qualifier="async_memory")
async def _async_memory_factory() -> _AsyncMemoryCache:
    return _AsyncMemoryCache()


@injectable
class _AsyncCacheConsumer:
    def __init__(self, caches: Injected[Set[_AsyncCache]]) -> None:
        self.caches = caches


async def test_async_container_resolves_set_of_async_impls() -> None:
    container = wireup.create_async_container(
        injectables=[_async_redis_factory, _async_memory_factory, _AsyncCacheConsumer],
    )
    consumer = await container.get(_AsyncCacheConsumer)

    assert len(consumer.caches) == 2
    tags = {cache.tag() for cache in consumer.caches}
    assert tags == {"async_redis", "async_memory"}

    compiled_factory = container._factories[_AsyncCacheConsumer]
    assert "_resolve_collection_set_async" in compiled_factory.generated_source
    assert "await container._resolve_collection_set_async" in compiled_factory.generated_source
