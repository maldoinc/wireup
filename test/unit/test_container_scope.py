from typing import Iterator

import wireup
from wireup.ioc.types import ServiceLifetime


class SingletonService: ...


class ScopedService: ...


def test_scoped_exit_does_not_close_singleton_scopes() -> None:
    singleton_service_factory_exited = False

    def singleton_service_factory() -> Iterator[SingletonService]:
        yield SingletonService()
        nonlocal singleton_service_factory_exited
        singleton_service_factory_exited = True

    c = wireup.create_sync_container()
    c._registry.register(singleton_service_factory)

    with wireup.enter_scope(c) as scoped:
        scoped.get(SingletonService)

    assert not singleton_service_factory_exited


async def test_scoped_exit_does_not_close_singleton_scopes_async() -> None:
    singleton_service_factory_exited = False

    def singleton_service_factory() -> Iterator[SingletonService]:
        yield SingletonService()
        nonlocal singleton_service_factory_exited
        singleton_service_factory_exited = True

    c = wireup.create_async_container()
    c._registry.register(singleton_service_factory)

    async with wireup.enter_async_scope(c) as scoped:
        await scoped.get(SingletonService)

    assert not singleton_service_factory_exited


def test_scoped_container_singleton_in_scope() -> None:
    c = wireup.create_sync_container()
    c._registry.register(SingletonService)

    singleton1 = c.get(SingletonService)

    with wireup.enter_scope(c) as scoped:
        assert scoped.get(SingletonService) is singleton1


def test_scoped_container_reuses_instance_container_get() -> None:
    c = wireup.create_sync_container()
    c._registry.register(ScopedService, lifetime=ServiceLifetime.SCOPED)

    with wireup.enter_scope(c) as scoped:
        assert scoped.get(ScopedService) is scoped.get(ScopedService)


def test_scoped_container_multiple_scopes() -> None:
    c = wireup.create_sync_container()
    c._registry.register(ScopedService, lifetime=ServiceLifetime.SCOPED)

    with wireup.enter_scope(c) as scoped1, wireup.enter_scope(c) as scoped2:
        assert scoped1 is not scoped2
        assert scoped1.get(ScopedService) is scoped1.get(ScopedService)
        assert scoped2.get(ScopedService) is scoped2.get(ScopedService)
        assert scoped1.get(ScopedService) is not scoped2.get(ScopedService)


def test_scoped_container_cleansup_container_get() -> None:
    class SomeService: ...

    done = False

    def factory() -> Iterator[SomeService]:
        yield SomeService()
        nonlocal done
        done = True

    c = wireup.create_sync_container()
    c._registry.register(factory, lifetime=ServiceLifetime.TRANSIENT)

    with wireup.enter_scope(c) as scoped:
        assert scoped.get(SomeService)

    assert done
