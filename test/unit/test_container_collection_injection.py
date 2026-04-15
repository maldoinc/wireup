from __future__ import annotations

import typing
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional, Protocol

import pytest
from wireup import Injected, create_sync_container, inject_from_container, injectable
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
