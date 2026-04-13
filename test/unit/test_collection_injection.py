from __future__ import annotations

import inspect
import re
import typing
import warnings
from abc import ABC, abstractmethod
from collections import abc  # noqa: TC003

import pytest
import wireup
from wireup import Injected, injectable
from wireup.errors import UnknownServiceRequestedError, WireupError
from wireup.ioc.types import CollectionKind
from wireup.ioc.util import (
    get_inject_annotated_parameters,
    get_valid_injection_annotated_parameters,
    injection_requires_scope,
    param_get_annotation,
)


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
    assert result.qualifier_value is CollectionKind.SET


def test_injects_set_of_qualified_cache_impls() -> None:
    container = wireup.create_sync_container(
        injectables=[RedisCache, InMemoryCache, CacheConsumer],
    )
    consumer = container.get(CacheConsumer)

    assert len(consumer.caches) == 2
    names = {cache.name() for cache in consumer.caches}
    assert names == {"redis", "in_memory"}


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


@injectable
class _SingletonConsumerOfScopedCollection:
    def __init__(self, caches: Injected[set[_ScopedCache]]) -> None:
        self.caches = caches


def test_rejects_singleton_consumer_of_non_singleton_collection() -> None:
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


@injectable
class _CycleConsumer:
    def __init__(self, impls: Injected[set[_CycleInterface]]) -> None:
        self.impls = impls


@injectable(as_type=_CycleInterface, qualifier="cycle_a")
class _CycleImplA(_CycleInterface):
    def __init__(self, consumer: _CycleConsumer) -> None:
        self.consumer = consumer

    def tag(self) -> str:
        return "a"


def test_rejects_cycle_through_collection_dep() -> None:
    with pytest.raises(WireupError, match=re.escape("Circular dependency")):
        wireup.create_sync_container(injectables=[_CycleImplA, _CycleConsumer])


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


def test_inject_from_container_resolves_set_of_impls() -> None:
    container = wireup.create_sync_container(injectables=[RedisCache, InMemoryCache])

    @wireup.inject_from_container(container)
    def handler(caches: Injected[set[Cache]]) -> set[str]:
        return {cache.name() for cache in caches}

    result = handler()
    assert result == {"redis", "in_memory"}


class _EmptyCache(ABC):
    @abstractmethod
    def label(self) -> str: ...


@injectable
class _EmptyCacheConsumer:
    def __init__(self, caches: Injected[set[_EmptyCache]]) -> None:
        self.caches = caches


def test_consumer_of_collection_with_no_impls_receives_empty_set() -> None:
    container = wireup.create_sync_container(injectables=[_EmptyCacheConsumer])
    consumer = container.get(_EmptyCacheConsumer)
    assert consumer.caches == set()


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


def test_injects_mix_of_qualified_and_unqualified_impls() -> None:
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

    with pytest.raises(UnknownServiceRequestedError):
        container.get(set[Cache])


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


@injectable(qualifier="tv_player")
def _tv_player_builder(producer: _ProducerTransport) -> _DeviceBuilder:
    return _DeviceBuilder("tv_player", producer.tag)


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


with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)

    @wireup.abstract
    class _InheritBase(ABC):
        @abstractmethod
        def label(self) -> str: ...


@wireup.injectable(qualifier="alpha")
class _InheritAlpha(_InheritBase):
    def label(self) -> str:
        return "alpha"


@wireup.injectable(qualifier="beta")
class _InheritBeta(_InheritBase):
    def label(self) -> str:
        return "beta"


@wireup.injectable
class _InheritConsumer:
    def __init__(self, impls: Injected[set[_InheritBase]]) -> None:
        self.impls = impls


def test_set_of_impls_resolves_via_wireup_abstract_interface() -> None:
    container = wireup.create_sync_container(
        injectables=[_InheritBase, _InheritAlpha, _InheritBeta, _InheritConsumer],
    )

    consumer = container.get(_InheritConsumer)
    labels = {impl.label() for impl in consumer.impls}
    assert labels == {"alpha", "beta"}


class _PureCheckCache(ABC):
    @abstractmethod
    def tag(self) -> str: ...


@injectable(as_type=_PureCheckCache, qualifier="alpha")
class _PureCheckCacheAlpha(_PureCheckCache):
    def tag(self) -> str:
        return "alpha"


def _pure_check_target(caches: Injected[set[_PureCheckCache]]) -> set[str]:
    return {cache.tag() for cache in caches}


def test_injection_requires_scope_does_not_mutate_after_synthesis() -> None:
    container = wireup.create_sync_container(injectables=[_PureCheckCacheAlpha])

    names_to_inject = get_inject_annotated_parameters(_pure_check_target)
    container._registry.register_collection_factories_for(names_to_inject)

    factories_before = dict(container._registry.factories)
    dependencies_before = dict(container._registry.dependencies)
    lifetime_before = dict(container._registry.lifetime)

    on_change_calls = 0

    def _count_calls() -> None:
        nonlocal on_change_calls
        on_change_calls += 1

    container._registry.on_change = _count_calls

    for _ in range(3):
        injection_requires_scope(names_to_inject, container)

    assert on_change_calls == 0
    assert container._registry.factories == factories_before
    assert container._registry.dependencies == dependencies_before
    assert container._registry.lifetime == lifetime_before


def test_get_valid_injection_annotated_parameters_synthesizes_collection_factory() -> None:
    container = wireup.create_sync_container(injectables=[_PureCheckCacheAlpha])

    collection_obj_id = (_PureCheckCache, CollectionKind.SET)
    assert collection_obj_id not in container._registry.factories

    get_valid_injection_annotated_parameters(container, _pure_check_target)

    assert collection_obj_id in container._registry.factories


def test_factory_functions_with_heterogeneous_deps_resolve_in_set() -> None:
    container = wireup.create_sync_container(
        injectables=[
            _make_producer_transport,
            _make_logger,
            _tv_player_builder,
            _generic_player_builder,
            _logged_device_builder,
            _DeviceLifecycleService,
        ],
    )
    service = container.get(_DeviceLifecycleService)

    by_type = {builder.device_type: builder.extra for builder in service.builders}
    assert by_type == {
        "tv_player": "producer",
        "generic_player": "none",
        "logged_device": "logger",
    }


@injectable
class _DeviceLifecycleServiceByType:
    def __init__(self, builders: Injected[typing.Mapping[str, _DeviceBuilder]]) -> None:
        self.builders = builders


def test_factory_functions_with_heterogeneous_deps_resolve_in_mapping() -> None:
    container = wireup.create_sync_container(
        injectables=[
            _make_producer_transport,
            _make_logger,
            _tv_player_builder,
            _generic_player_builder,
            _logged_device_builder,
            _DeviceLifecycleServiceByType,
        ],
    )
    service = container.get(_DeviceLifecycleServiceByType)

    assert set(service.builders.keys()) == {"tv_player", "generic_player", "logged_device"}
    assert service.builders["tv_player"].extra == "producer"
    assert service.builders["generic_player"].extra == "none"
    assert service.builders["logged_device"].extra == "logger"


@injectable
class MappingCacheConsumer:
    def __init__(self, caches: Injected[typing.Mapping[str, Cache]]) -> None:
        self.caches = caches


def test_injects_mapping_of_qualified_cache_impls() -> None:
    container = wireup.create_sync_container(
        injectables=[RedisCache, InMemoryCache, MappingCacheConsumer],
    )
    consumer = container.get(MappingCacheConsumer)

    assert isinstance(consumer.caches, dict)
    assert set(consumer.caches.keys()) == {"redis", "in_memory"}
    assert consumer.caches["redis"].name() == "redis"
    assert consumer.caches["in_memory"].name() == "in_memory"


def test_param_get_annotation_detects_mapping_of_interface() -> None:
    def target(caches: typing.Mapping[str, Cache]) -> None: ...

    parameter = inspect.signature(target).parameters["caches"]
    result = param_get_annotation(parameter, globalns_supplier=lambda: globals())

    assert result is not None
    assert result.klass is Cache
    assert result.qualifier_value is CollectionKind.MAP


class _MappedCache(ABC):
    @abstractmethod
    def tag(self) -> str: ...


@injectable(as_type=_MappedCache)
class _MappedDefaultCache(_MappedCache):
    def tag(self) -> str:
        return "default"


@injectable(as_type=_MappedCache, qualifier="alpha")
class _MappedAlphaCache(_MappedCache):
    def tag(self) -> str:
        return "alpha"


@injectable(as_type=_MappedCache, qualifier="beta")
class _MappedBetaCache(_MappedCache):
    def tag(self) -> str:
        return "beta"


@injectable
class _MappedConsumer:
    def __init__(self, caches: Injected[typing.Mapping[str, _MappedCache]]) -> None:
        self.caches = caches


def test_mapping_excludes_unqualified_impls() -> None:
    container = wireup.create_sync_container(
        injectables=[_MappedDefaultCache, _MappedAlphaCache, _MappedBetaCache, _MappedConsumer],
    )
    consumer = container.get(_MappedConsumer)

    assert set(consumer.caches.keys()) == {"alpha", "beta"}
    assert consumer.caches["alpha"].tag() == "alpha"
    assert consumer.caches["beta"].tag() == "beta"


def test_mapping_all_four_spellings_resolve_identically() -> None:
    def t1(caches: typing.Mapping[str, Cache]) -> None: ...
    def t2(caches: typing.Dict[str, Cache]) -> None: ...  # noqa: UP006
    def t3(caches: dict[str, Cache]) -> None: ...
    def t4(caches: abc.Mapping[str, Cache]) -> None: ...

    results = [
        param_get_annotation(
            inspect.signature(fn).parameters["caches"],
            globalns_supplier=lambda: globals(),
        )
        for fn in (t1, t2, t3, t4)
    ]

    for result in results:
        assert result is not None
        assert result.klass is Cache
        assert result.qualifier_value is CollectionKind.MAP


def test_rejects_mapping_with_non_str_key() -> None:
    @injectable
    class BadConsumer:
        def __init__(self, caches: Injected[typing.Mapping[int, Cache]]) -> None:
            self.caches = caches

    with pytest.raises(WireupError, match=re.escape("only Mapping[str, T] is supported")):
        wireup.create_sync_container(injectables=[RedisCache, InMemoryCache, BadConsumer])


@injectable
class _AsyncMappingCacheConsumer:
    def __init__(self, caches: Injected[typing.Mapping[str, _AsyncCache]]) -> None:
        self.caches = caches


@injectable
class _SetAndMapConsumer:
    def __init__(
        self,
        caches_set: Injected[set[Cache]],
        caches_map: Injected[typing.Mapping[str, Cache]],
    ) -> None:
        self.caches_set = caches_set
        self.caches_map = caches_map


def test_injects_same_interface_as_both_set_and_mapping() -> None:
    container = wireup.create_sync_container(
        injectables=[RedisCache, InMemoryCache, _SetAndMapConsumer],
    )
    consumer = container.get(_SetAndMapConsumer)

    assert {c.name() for c in consumer.caches_set} == {"redis", "in_memory"}
    assert set(consumer.caches_map.keys()) == {"redis", "in_memory"}


async def test_async_container_resolves_mapping_of_async_impls() -> None:
    container = wireup.create_async_container(
        injectables=[_async_redis_factory, _async_memory_factory, _AsyncMappingCacheConsumer],
    )
    consumer = await container.get(_AsyncMappingCacheConsumer)

    assert isinstance(consumer.caches, dict)
    assert set(consumer.caches.keys()) == {"async_redis", "async_memory"}

    collection_obj_id = (_AsyncCache, CollectionKind.MAP)
    assert collection_obj_id in container._factories
    assert container._factories[collection_obj_id].is_async
