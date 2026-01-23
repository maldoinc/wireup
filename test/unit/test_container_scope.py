from typing import Iterator
from unittest.mock import MagicMock

import wireup
from wireup import create_sync_container, injectable

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


@injectable
class Database:
    def __init__(self) -> None:
        self.name = "default_db"


@injectable
class UserService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_db_name(self) -> str:
        return self.db.name


def test_override_dict():
    @injectable(qualifier="cache")
    def cache_db_factory() -> Database:
        db = Database()
        db.name = "cache"
        return db

    container = create_sync_container(injectables=[Database, UserService, cache_db_factory])

    mock_db = MagicMock()
    mock_cache = MagicMock()

    with container.override(
        {
            Database: mock_db,
            (Database, "cache"): mock_cache,
        }
    ):
        assert container.get(Database) is mock_db
        assert container.get(Database, qualifier="cache") is mock_cache


def test_empty_dict_override():
    container = create_sync_container(injectables=[Database, UserService])

    with container.override({}):
        service = container.get(UserService)
        assert service.get_db_name() == "default_db"
