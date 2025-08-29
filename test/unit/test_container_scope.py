from typing import Iterator

import pytest
import wireup
from wireup._annotations import service
from wireup.errors import ContainerCloseError

from test.unit.services.with_annotations.services import TransientService


@service
class SingletonService: ...


@service(lifetime="scoped")
class ScopedService: ...


def test_scoped_exit_does_not_close_singleton_scopes() -> None:
    singleton_service_factory_exited = False

    @service
    def singleton_service_factory() -> Iterator[SingletonService]:
        yield SingletonService()
        nonlocal singleton_service_factory_exited
        singleton_service_factory_exited = True

    c = wireup.create_sync_container(services=[singleton_service_factory])

    with c.enter_scope() as scoped:
        scoped.get(SingletonService)

    assert not singleton_service_factory_exited


async def test_scoped_exit_does_not_close_singleton_scopes_async() -> None:
    singleton_service_factory_exited = False

    @service
    def singleton_service_factory() -> Iterator[SingletonService]:
        yield SingletonService()
        nonlocal singleton_service_factory_exited
        singleton_service_factory_exited = True

    c = wireup.create_async_container(services=[singleton_service_factory])

    async with c.enter_scope() as scoped:
        await scoped.get(SingletonService)

    assert not singleton_service_factory_exited


def test_scoped_container_singleton_in_scope() -> None:
    c = wireup.create_sync_container(services=[SingletonService])

    singleton1 = c.get(SingletonService)

    with c.enter_scope() as scoped:
        assert scoped.get(SingletonService) is singleton1


def test_does_not_reuse_transient_service() -> None:
    c = wireup.create_sync_container(services=[TransientService])

    with c.enter_scope() as scoped:
        assert scoped.get(TransientService) is not scoped.get(TransientService)


def test_scoped_container_reuses_instance_container_get() -> None:
    c = wireup.create_sync_container(services=[ScopedService])

    with c.enter_scope() as scoped:
        assert scoped.get(ScopedService) is scoped.get(ScopedService)


def test_scoped_container_multiple_scopes() -> None:
    c = wireup.create_sync_container(services=[ScopedService])

    with c.enter_scope() as scoped1, c.enter_scope() as scoped2:
        assert scoped1 is not scoped2
        assert scoped1.get(ScopedService) is scoped1.get(ScopedService)
        assert scoped2.get(ScopedService) is scoped2.get(ScopedService)
        assert scoped1.get(ScopedService) is not scoped2.get(ScopedService)


def test_scoped_container_cleansup_container_get() -> None:
    class SomeService: ...

    done = False

    @service(lifetime="transient")
    def factory() -> Iterator[SomeService]:
        yield SomeService()
        nonlocal done
        done = True

    c = wireup.create_sync_container(services=[factory])

    with c.enter_scope() as scoped:
        assert scoped.get(SomeService)

    assert done


def test_scoped_container_exit_with_exception_primary_exception_close_container_exceptions() -> None:
    """Test that when closing a scoped container with an exception, the primary exception is preserved
    and container close exceptions are chained"""

    class SomeService: ...

    cleanup_error = False

    @service(lifetime="transient")
    def factory() -> Iterator[SomeService]:
        try:
            yield SomeService()
        except ValueError:
            nonlocal cleanup_error
            cleanup_error = True
            raise RuntimeError("cleanup failed") from None

    c = wireup.create_sync_container(services=[factory])

    with pytest.raises(ValueError, match="original error") as exc_info:
        with c.enter_scope() as scoped:
            scoped.get(SomeService)
            raise ValueError("original error")

    # The cleanup should have been attempted
    assert cleanup_error
    # The original exception should be raised, chained with ContainerCloseError
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, ContainerCloseError)
    cause = exc_info.value.__cause__
    assert isinstance(cause, ContainerCloseError)
    assert len(cause.errors) == 1
    assert isinstance(cause.errors[0], RuntimeError)
    assert str(cause.errors[0]) == "cleanup failed"


async def test_scoped_async_container_exit_with_exception_primary_exception_close_container_exceptions() -> None:
    """Test that when closing a scoped container with an exception, the primary exception is preserved
    and container close exceptions are chained"""

    class SomeService: ...

    cleanup_error = False

    @service(lifetime="transient")
    def factory() -> Iterator[SomeService]:
        try:
            yield SomeService()
        except ValueError:
            nonlocal cleanup_error
            cleanup_error = True
            raise RuntimeError("async cleanup failed") from None

    c = wireup.create_async_container(services=[factory])

    with pytest.raises(ValueError, match="original async error") as exc_info:
        async with c.enter_scope() as scoped:
            await scoped.get(SomeService)
            raise ValueError("original async error")

    # The cleanup should have been attempted
    assert cleanup_error
    # The original exception should be raised, chained with ContainerCloseError
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, ContainerCloseError)
    cause = exc_info.value.__cause__
    assert isinstance(cause, ContainerCloseError)
    assert len(cause.errors) == 1
    assert isinstance(cause.errors[0], RuntimeError)
    assert str(cause.errors[0]) == "async cleanup failed"
