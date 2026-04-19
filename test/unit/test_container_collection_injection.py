from __future__ import annotations

import typing
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, NewType, Optional, Protocol

import pytest
from wireup import Inject, Injected, create_sync_container, inject_from_container, injectable
from wireup._annotations import InjectableDeclaration
from wireup.errors import UnknownServiceRequestedError, WireupError
from wireup.ioc.registry import ContainerRegistry


class Cache(Protocol):
    def source(self) -> str: ...


@injectable(as_type=Cache)
class MemoryCache:
    def source(self) -> str:
        return "memory"


@injectable(as_type=Cache, qualifier="redis")
class RedisCache:
    def source(self) -> str:
        return "redis"


@injectable(as_type=Cache, qualifier="memory")
class QualifiedMemoryCache:
    def source(self) -> str:
        return "memory"


def test_injects_collection_sequence_for_as_type() -> None:
    container = create_sync_container(injectables=[MemoryCache, RedisCache])

    @inject_from_container(container)
    def handler(caches: Injected[Sequence[Cache]]) -> tuple[Cache, ...]:
        return tuple(caches)

    res = handler()
    assert isinstance(res, tuple)
    assert [cache.source() for cache in res] == ["memory", "redis"]
    assert container.get(Sequence[Cache]) is container.get(Sequence[Cache])


def test_injects_collection_sequence_for_single_implementation() -> None:
    container = create_sync_container(injectables=[MemoryCache])
    res = container.get(Sequence[Cache])

    assert isinstance(res, tuple)
    assert len(res) == 1
    assert res[0].source() == "memory"


def test_collection_lifetime_is_smallest_member_lifetime() -> None:
    @injectable(as_type=Cache)
    class SingletonCache:
        def source(self) -> str:
            return "singleton"

    @injectable(as_type=Cache, qualifier="scoped", lifetime="scoped")
    class ScopedCache:
        def source(self) -> str:
            return "scoped"

    @injectable
    @dataclass
    class Consumer:
        caches: Sequence[Cache]

    with pytest.raises(
        WireupError,
        match="depends on an injectable with a 'scoped' lifetime which is not supported",
    ):
        create_sync_container(injectables=[SingletonCache, ScopedCache, Consumer])


def test_can_override_collection_directly() -> None:
    class OverrideCache:
        def source(self) -> str:
            return "override"

    container = create_sync_container(injectables=[MemoryCache, RedisCache])
    override_caches = (OverrideCache(), RedisCache())

    assert [cache.source() for cache in container.get(Sequence[Cache])] == ["memory", "redis"]
    with container.override.injectable(Sequence[Cache], new=override_caches):
        assert [cache.source() for cache in container.get(Sequence[Cache])] == ["override", "redis"]

    assert [cache.source() for cache in container.get(Sequence[Cache])] == ["memory", "redis"]


def test_explicit_sequence_registration_takes_precedence_and_warns() -> None:
    seq = [MemoryCache()]

    @injectable
    def make_custom_sequence() -> Sequence[Cache]:
        return seq

    with pytest.warns(FutureWarning, match=r"Wireup did not register collection injection for .*Sequence"):
        container = create_sync_container(injectables=[MemoryCache, make_custom_sequence])

    assert container.get(Sequence[Cache]) is seq


def test_injects_collection_when_registration_key_comes_from_factory_return_type() -> None:
    @injectable
    def make_default_cache() -> Cache:
        return MemoryCache()

    @injectable(qualifier="redis")
    def make_redis_cache() -> Cache:
        return RedisCache()

    container = create_sync_container(injectables=[make_default_cache, make_redis_cache])
    res = container.get(Sequence[Cache])

    assert isinstance(res, tuple)
    assert [cache.source() for cache in res] == ["memory", "redis"]


def test_internal_extend_does_not_create_nested_sequence_collections() -> None:
    registry = ContainerRegistry(impls=[InjectableDeclaration(obj=MemoryCache, lifetime="singleton")])

    @injectable
    class ExtraService:
        pass

    registry.extend(impls=[InjectableDeclaration(obj=ExtraService, lifetime="singleton")])

    assert Sequence[Sequence[MemoryCache]] not in registry.impls


def test_optional_compat_alias_does_not_create_sequence_of_raw_type() -> None:
    @injectable
    def make_cache() -> Cache | None:
        return None

    container = create_sync_container(injectables=[make_cache])

    with pytest.raises(UnknownServiceRequestedError):
        container.get(Sequence[Cache])

    assert container.get(Sequence[Optional[Cache]]) == (None,)


def test_mixed_real_and_optional_compat_registrations_only_include_real_members_in_sequence() -> None:
    @injectable
    def make_optional_default_cache() -> Cache | None:
        return None

    @injectable(qualifier="redis")
    def make_redis_cache() -> Cache:
        return RedisCache()

    container = create_sync_container(injectables=[make_optional_default_cache, make_redis_cache])

    assert container.get(Sequence[Cache]) == (container.get(Cache, qualifier="redis"),)
    assert container.get(Sequence[Optional[Cache]]) == (None,)


def test_typing_sequence_is_not_registered() -> None:
    container = create_sync_container(injectables=[MemoryCache, RedisCache])

    with pytest.raises(UnknownServiceRequestedError):
        container.get(typing.Sequence[Cache])


def test_injects_collection_mapping_for_as_type() -> None:
    container = create_sync_container(injectables=[QualifiedMemoryCache, RedisCache])

    @inject_from_container(container)
    def handler(caches: Injected[Mapping[str, Cache]]) -> dict[str, str]:
        return {key: cache.source() for key, cache in caches.items()}

    assert handler() == {"memory": "memory", "redis": "redis"}
    assert container.get(Mapping[str, Cache]) is container.get(Mapping[str, Cache])


def test_injects_collection_mapping_for_single_implementation() -> None:
    container = create_sync_container(injectables=[RedisCache])
    res = container.get(Mapping[str, Cache])

    assert isinstance(res, dict)
    assert list(res.keys()) == ["redis"]
    assert res["redis"].source() == "redis"


def test_mapping_excludes_unqualified_default_impl() -> None:
    container = create_sync_container(injectables=[MemoryCache, RedisCache])
    res = container.get(Mapping[str, Cache])

    assert set(res.keys()) == {"redis"}
    assert res["redis"].source() == "redis"


def test_mapping_not_registered_when_only_unqualified_impls_exist() -> None:
    container = create_sync_container(injectables=[MemoryCache])

    with pytest.raises(UnknownServiceRequestedError):
        container.get(Mapping[str, Cache])


def test_mapping_lifetime_is_smallest_member_lifetime() -> None:
    @injectable(as_type=Cache, qualifier="default")
    class DefaultCache:
        def source(self) -> str:
            return "default"

    @injectable(as_type=Cache, qualifier="scoped", lifetime="scoped")
    class ScopedCache:
        def source(self) -> str:
            return "scoped"

    @injectable
    @dataclass
    class Consumer:
        caches: Mapping[str, Cache]

    with pytest.raises(
        WireupError,
        match="depends on an injectable with a 'scoped' lifetime which is not supported",
    ):
        create_sync_container(injectables=[DefaultCache, ScopedCache, Consumer])


def test_can_override_mapping_directly() -> None:
    container = create_sync_container(injectables=[QualifiedMemoryCache, RedisCache])
    override_map = {"override": RedisCache()}

    assert set(container.get(Mapping[str, Cache]).keys()) == {"memory", "redis"}
    with container.override.injectable(Mapping[str, Cache], new=override_map):
        assert container.get(Mapping[str, Cache]) is override_map
    assert set(container.get(Mapping[str, Cache]).keys()) == {"memory", "redis"}


def test_explicit_mapping_registration_takes_precedence_and_warns() -> None:
    mapping = {"custom": RedisCache()}

    @injectable
    def make_custom_mapping() -> Mapping[str, Cache]:
        return mapping

    with pytest.warns(FutureWarning, match=r"Wireup did not register collection injection for .*Mapping"):
        container = create_sync_container(injectables=[QualifiedMemoryCache, make_custom_mapping])

    assert container.get(Mapping[str, Cache]) is mapping


def test_injects_collection_mapping_when_registration_key_comes_from_factory_return_type() -> None:
    @injectable(qualifier="memory")
    def make_memory_cache() -> Cache:
        return MemoryCache()

    @injectable(qualifier="redis")
    def make_redis_cache() -> Cache:
        return RedisCache()

    container = create_sync_container(injectables=[make_memory_cache, make_redis_cache])
    res = container.get(Mapping[str, Cache])

    assert isinstance(res, dict)
    assert {key: cache.source() for key, cache in res.items()} == {"memory": "memory", "redis": "redis"}


def test_internal_extend_does_not_create_nested_mapping_collections() -> None:
    registry = ContainerRegistry(impls=[InjectableDeclaration(obj=QualifiedMemoryCache, lifetime="singleton")])

    @injectable
    class ExtraService:
        pass

    registry.extend(impls=[InjectableDeclaration(obj=ExtraService, lifetime="singleton")])

    assert Mapping[str, Mapping[str, QualifiedMemoryCache]] not in registry.impls


def test_mixed_real_and_optional_compat_registrations_only_include_real_members_in_mapping() -> None:
    @injectable
    def make_optional_default_cache() -> Cache | None:
        return None

    @injectable(qualifier="redis")
    def make_redis_cache() -> Cache:
        return RedisCache()

    container = create_sync_container(injectables=[make_optional_default_cache, make_redis_cache])

    assert container.get(Mapping[str, Cache]) == {"redis": container.get(Cache, qualifier="redis")}
    with pytest.raises(UnknownServiceRequestedError):
        container.get(Mapping[str, Optional[Cache]])


def test_typing_mapping_is_not_registered() -> None:
    container = create_sync_container(injectables=[QualifiedMemoryCache, RedisCache])

    with pytest.raises(UnknownServiceRequestedError, match=r"collections\.abc\.Mapping"):
        container.get(typing.Mapping[str, Cache])


def test_typing_dict_is_not_registered() -> None:
    container = create_sync_container(injectables=[QualifiedMemoryCache, RedisCache])

    with pytest.raises(UnknownServiceRequestedError, match=r"collections\.abc\.Mapping"):
        container.get(typing.Dict[str, Cache])


def test_builtin_dict_is_not_registered() -> None:
    container = create_sync_container(injectables=[QualifiedMemoryCache, RedisCache])

    with pytest.raises(UnknownServiceRequestedError, match=r"collections\.abc\.Mapping"):
        container.get(dict[str, Cache])


CacheMap = NewType("CacheMap", Mapping[str, Cache])


def test_newtype_over_mapping_registers_as_branded_collection() -> None:
    @injectable
    def make_cache_map(
        memory: Annotated[Cache, Inject(qualifier="memory")],
        redis: Annotated[Cache, Inject(qualifier="redis")],
    ) -> CacheMap:
        return CacheMap({"memory": memory, "redis": redis})

    container = create_sync_container(injectables=[QualifiedMemoryCache, RedisCache, make_cache_map])
    res = container.get(CacheMap)

    assert isinstance(res, dict)
    assert {key: cache.source() for key, cache in res.items()} == {"memory": "memory", "redis": "redis"}
