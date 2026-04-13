from __future__ import annotations

import inspect
import re
import typing
from abc import ABC, abstractmethod

import pytest
import wireup
from wireup import Injected, injectable
from wireup.errors import CollectionInterfaceUnknownError, WireupError
from wireup.ioc.types import CollectionKind, InjectableQualifier
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
    def __init__(self, caches: Injected[set[Cache]]) -> None:
        self.caches = caches


def test_param_get_annotation_detects_set_of_interface() -> None:
    def target(caches: set[Cache]) -> None: ...

    parameter = inspect.signature(target).parameters["caches"]
    result = param_get_annotation(parameter, globalns_supplier=lambda: globals())

    assert result is not None
    assert result.klass is Cache
    assert isinstance(result.annotation, InjectableQualifier)
    assert result.annotation.qualifier is CollectionKind.SET
    assert result.qualifier_value is CollectionKind.SET


def test_param_get_annotation_detects_injected_set_of_interface() -> None:
    def target(caches: Injected[set[Cache]]) -> None: ...

    parameter = inspect.signature(target).parameters["caches"]
    result = param_get_annotation(parameter, globalns_supplier=lambda: globals())

    assert result is not None
    assert result.klass is Cache
    assert result.qualifier_value is CollectionKind.SET


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
        def __init__(self, impls: Injected[set[_UnknownInterface]]) -> None:
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
    def __init__(self, caches: Injected[set[_ScopedCache]]) -> None:
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
    def __init__(self, consumer: _CycleConsumer) -> None:  # type: ignore[name-defined]
        self.consumer = consumer

    def tag(self) -> str:
        return "a"


@injectable
class _CycleConsumer:
    def __init__(self, impls: Injected[set[_CycleInterface]]) -> None:
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
    def __init__(self, caches: Injected[set[_AsyncCache]]) -> None:
        self.caches = caches


async def test_async_container_resolves_set_of_async_impls() -> None:
    container = wireup.create_async_container(
        injectables=[_async_redis_factory, _async_memory_factory, _AsyncCacheConsumer],
    )
    consumer = await container.get(_AsyncCacheConsumer)

    assert len(consumer.caches) == 2
    tags = {cache.tag() for cache in consumer.caches}
    assert tags == {"async_redis", "async_memory"}

    # The synthesized collection factory is registered under (_AsyncCache, CollectionKind.SET)
    # and async-flag propagation marks the consumer as async. The consumer's generated code
    # resolves the collection through the standard service-branch dict lookup.
    collection_obj_id = (_AsyncCache, CollectionKind.SET)
    assert collection_obj_id in container._factories
    assert container._factories[collection_obj_id].is_async

    consumer_compiled = container._factories[_AsyncCacheConsumer]
    assert "factories[" in consumer_compiled.generated_source
    assert "await factories[" in consumer_compiled.generated_source


# ---- inject_from_container path ----


def test_inject_from_container_resolves_set_of_impls() -> None:
    container = wireup.create_sync_container(injectables=[RedisCache, InMemoryCache])

    @wireup.inject_from_container(container)
    def handler(caches: Injected[set[Cache]]) -> set[str]:
        return {cache.name() for cache in caches}

    result = handler()
    assert result == {"redis", "in_memory"}


# ---- Edge cases ----


class _EmptyCache(ABC):
    @abstractmethod
    def label(self) -> str: ...


@injectable
class _EmptyCacheConsumer:
    def __init__(self, caches: Injected[set[_EmptyCache]]) -> None:
        self.caches = caches


def test_consumer_of_collection_with_no_impls_is_rejected_at_build_time() -> None:
    # When the inner type has zero registered implementations, validation rejects the
    # consumer with CollectionInterfaceUnknownError. Users who want an "empty collection
    # is fine" semantic must register the type via at least one entry (even a placeholder).
    with pytest.raises(CollectionInterfaceUnknownError):
        wireup.create_sync_container(injectables=[_EmptyCacheConsumer])


class _MixedCache(ABC):
    @abstractmethod
    def tag(self) -> str: ...


@injectable(as_type=_MixedCache)
class _MixedDefaultCache(_MixedCache):
    def tag(self) -> str:
        return "default"


@injectable(as_type=_MixedCache, qualifier="left")
class _MixedLeftCache(_MixedCache):
    def tag(self) -> str:
        return "left"


@injectable(as_type=_MixedCache, qualifier="right")
class _MixedRightCache(_MixedCache):
    def tag(self) -> str:
        return "right"


@injectable
class _MixedConsumer:
    def __init__(self, caches: Injected[set[_MixedCache]]) -> None:
        self.caches = caches


def test_unqualified_and_qualified_impls_all_appear_in_set() -> None:
    container = wireup.create_sync_container(
        injectables=[_MixedDefaultCache, _MixedLeftCache, _MixedRightCache, _MixedConsumer],
    )
    consumer = container.get(_MixedConsumer)
    tags = {cache.tag() for cache in consumer.caches}
    assert tags == {"default", "left", "right"}


def test_typing_set_alias_and_set_spelling_resolve_identically() -> None:
    def target_lowercase(caches: Injected[set[Cache]]) -> None: ...
    def target_typing(caches: Injected[typing.Set[Cache]]) -> None: ...  # noqa: UP006

    lowercase_param = inspect.signature(target_lowercase).parameters["caches"]
    typing_param = inspect.signature(target_typing).parameters["caches"]

    lowercase_result = param_get_annotation(lowercase_param, globalns_supplier=lambda: globals())
    typing_result = param_get_annotation(typing_param, globalns_supplier=lambda: globals())

    assert lowercase_result is not None
    assert typing_result is not None
    assert lowercase_result.qualifier_value is CollectionKind.SET
    assert typing_result.qualifier_value is CollectionKind.SET
    assert lowercase_result.klass is Cache
    assert typing_result.klass is Cache


def test_top_level_container_get_on_parameterized_set_raises() -> None:
    container = wireup.create_sync_container(injectables=[RedisCache, InMemoryCache])

    with pytest.raises(Exception) as exc_info:
        container.get(set[Cache])

    # Error should surface something intelligible — not a KeyError inside the factory dict.
    assert "set" in str(exc_info.value).lower() or "unknown" in str(exc_info.value).lower()


# ---- Factory functions with heterogeneous deps (the downstream DeviceBuilder pattern) ----


class _ProducerTransport:
    def __init__(self) -> None:
        self.tag = "producer"


class _Logger:
    def __init__(self) -> None:
        self.tag = "logger"


@injectable
def _make_producer_transport() -> _ProducerTransport:
    return _ProducerTransport()


@injectable
def _make_logger() -> _Logger:
    return _Logger()


class _DeviceBuilder:
    def __init__(self, device_type: str, extra: str) -> None:
        self.device_type = device_type
        self.extra = extra


@injectable(qualifier="apple_tv")
def _apple_tv_builder(producer: _ProducerTransport) -> _DeviceBuilder:
    return _DeviceBuilder("apple_tv", producer.tag)


@injectable(qualifier="generic_player")
def _generic_player_builder() -> _DeviceBuilder:
    return _DeviceBuilder("generic_player", "none")


@injectable(qualifier="logged_device")
def _logged_device_builder(logger: _Logger) -> _DeviceBuilder:
    return _DeviceBuilder("logged_device", logger.tag)


@injectable
class _DeviceLifecycleService:
    def __init__(self, builders: Injected[set[_DeviceBuilder]]) -> None:
        self.builders = builders


def test_factory_functions_with_heterogeneous_deps_resolve_in_set() -> None:
    container = wireup.create_sync_container(
        injectables=[
            _make_producer_transport,
            _make_logger,
            _apple_tv_builder,
            _generic_player_builder,
            _logged_device_builder,
            _DeviceLifecycleService,
        ],
    )
    service = container.get(_DeviceLifecycleService)

    by_type = {builder.device_type: builder.extra for builder in service.builders}
    assert by_type == {
        "apple_tv": "producer",
        "generic_player": "none",
        "logged_device": "logger",
    }
