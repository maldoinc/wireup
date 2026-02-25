from typing import Iterator

import pytest
import wireup
from wireup._annotations import injectable

from test.unit.services.with_annotations.services import TransientService


@injectable
class SingletonService: ...


@injectable(lifetime="scoped")
class ScopedService: ...


def test_scoped_exit_does_not_close_singleton_scopes() -> None:
    singleton_service_factory_exited = False

    @injectable
    def singleton_service_factory() -> Iterator[SingletonService]:
        yield SingletonService()
        nonlocal singleton_service_factory_exited
        singleton_service_factory_exited = True

    c = wireup.create_sync_container(injectables=[singleton_service_factory])

    with c.enter_scope() as scoped:
        scoped.get(SingletonService)

    assert not singleton_service_factory_exited


async def test_scoped_exit_does_not_close_singleton_scopes_async() -> None:
    singleton_service_factory_exited = False

    @injectable
    def singleton_service_factory() -> Iterator[SingletonService]:
        yield SingletonService()
        nonlocal singleton_service_factory_exited
        singleton_service_factory_exited = True

    c = wireup.create_async_container(injectables=[singleton_service_factory])

    async with c.enter_scope() as scoped:
        await scoped.get(SingletonService)

    assert not singleton_service_factory_exited


def test_scoped_container_singleton_in_scope() -> None:
    c = wireup.create_sync_container(injectables=[SingletonService])

    singleton1 = c.get(SingletonService)

    with c.enter_scope() as scoped:
        assert scoped.get(SingletonService) is singleton1


def test_does_not_reuse_transient_service() -> None:
    c = wireup.create_sync_container(injectables=[TransientService])

    with c.enter_scope() as scoped:
        assert scoped.get(TransientService) is not scoped.get(TransientService)


def test_scoped_container_reuses_instance_container_get() -> None:
    c = wireup.create_sync_container(injectables=[ScopedService])

    with c.enter_scope() as scoped:
        assert scoped.get(ScopedService) is scoped.get(ScopedService)


def test_scoped_container_multiple_scopes() -> None:
    c = wireup.create_sync_container(injectables=[ScopedService])

    with c.enter_scope() as scoped1, c.enter_scope() as scoped2:
        assert scoped1 is not scoped2
        assert scoped1.get(ScopedService) is scoped1.get(ScopedService)
        assert scoped2.get(ScopedService) is scoped2.get(ScopedService)
        assert scoped1.get(ScopedService) is not scoped2.get(ScopedService)


def test_scoped_container_cleansup_container_get() -> None:
    class SomeService: ...

    done = False

    @injectable(lifetime="transient")
    def factory() -> Iterator[SomeService]:
        yield SomeService()
        nonlocal done
        done = True

    c = wireup.create_sync_container(injectables=[factory])

    with c.enter_scope() as scoped:
        assert scoped.get(SomeService)

    assert done


def test_scoped_qualifiers_do_not_collide_on_hash() -> None:
    @injectable(lifetime="scoped", qualifier=-2)
    def make_b1() -> int:
        return 666

    @injectable(lifetime="scoped", qualifier=-1)
    def make_b2() -> int:
        return 42

    c = wireup.create_sync_container(injectables=[make_b1, make_b2])

    with c.enter_scope() as scoped:
        assert scoped.get(int, qualifier=-1) == 42
        assert scoped.get(int, qualifier=-2) == 666


@pytest.mark.parametrize("qualifier", [0, False], ids=["zero", "false"])
def test_scoped_falsy_qualifier_is_distinct_from_none(qualifier: int) -> None:
    @injectable(lifetime="scoped")
    def make_default() -> int:
        return 11

    @injectable(lifetime="scoped", qualifier=qualifier)
    def make_qualified() -> int:
        return 22

    c = wireup.create_sync_container(injectables=[make_default, make_qualified])

    with c.enter_scope() as scoped:
        assert scoped.get(int) == 11
        assert scoped.get(int, qualifier=qualifier) == 22


@pytest.mark.parametrize("qualifier", [0, False], ids=["zero", "false"])
async def test_scoped_falsy_qualifier_is_distinct_from_none_async(qualifier: int) -> None:
    @injectable(lifetime="scoped")
    def make_default() -> int:
        return 11

    @injectable(lifetime="scoped", qualifier=qualifier)
    def make_qualified() -> int:
        return 22

    c = wireup.create_async_container(injectables=[make_default, make_qualified])

    async with c.enter_scope() as scoped:
        assert await scoped.get(int) == 11
        assert await scoped.get(int, qualifier=qualifier) == 22
