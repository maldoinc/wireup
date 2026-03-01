from typing import Iterator

import pytest
import wireup
from celery import Celery
from wireup import Injected, injectable
from wireup.errors import WireupError
from wireup.integration import celery as wireup_celery


@injectable
class NumberGenerator:
    def get_lucky_number(self) -> int:
        return 42


@pytest.fixture
def app() -> Celery:
    app = Celery("wireup_test")
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True
    return app


@pytest.fixture
def container() -> wireup.SyncContainer:
    return wireup.create_sync_container(injectables=[NumberGenerator])


def test_injects_dependencies(container: wireup.SyncContainer, app: Celery) -> None:
    @app.task(name="lucky_number")
    @wireup_celery.inject
    def lucky_number(generator: Injected[NumberGenerator]) -> int:  # type: ignore[reportUnusedFunction]
        return generator.get_lucky_number()

    wireup_celery.setup(container, app)

    result = lucky_number.delay()
    assert result.get() == 42


def test_injects_dependencies_when_decorator_order_is_reversed(container: wireup.SyncContainer, app: Celery) -> None:
    @wireup_celery.inject
    @app.task(name="lucky_number_reversed")
    def lucky_number_reversed(generator: Injected[NumberGenerator]) -> int:  # type: ignore[reportUnusedFunction]
        return generator.get_lucky_number()

    wireup_celery.setup(container, app)

    result = lucky_number_reversed.delay()
    assert result.get() == 42


def test_non_injected_tasks_keep_celery_default_behavior(container: wireup.SyncContainer, app: Celery) -> None:
    @app.task(name="not_injected")
    def not_injected(generator: Injected[NumberGenerator]) -> int:  # type: ignore[reportUnusedFunction]
        return generator.get_lucky_number()

    wireup_celery.setup(container, app)

    with pytest.raises(TypeError, match="missing 1 required positional argument: 'generator'"):
        not_injected.delay()


def test_container_access(container: wireup.SyncContainer, app: Celery) -> None:
    wireup_celery.setup(container, app)
    assert wireup_celery.get_app_container(app) == container  # type: ignore[reportAttributeAccessIssue]


def test_task_scope_created_and_cleaned_up(app: Celery) -> None:
    cleaned_up = {"done": False}

    class ScopedResource:
        def __init__(self) -> None:
            self.value = "ready"

    @injectable(lifetime="scoped")
    def make_scoped_resource() -> Iterator[ScopedResource]:
        try:
            yield ScopedResource()
        finally:
            cleaned_up["done"] = True

    container = wireup.create_sync_container(injectables=[make_scoped_resource])
    wireup_celery.setup(container, app)

    @app.task(name="scope_check")
    @wireup_celery.inject
    def scope_check(resource: Injected[ScopedResource]) -> str:  # type: ignore[reportUnusedFunction]
        scoped = wireup_celery.get_task_container()
        assert scoped.get(ScopedResource) is resource
        return resource.value

    result = scope_check.delay()
    assert result.get() == "ready"
    assert cleaned_up["done"] is True


def test_get_task_container_outside_task_raises() -> None:
    with pytest.raises(WireupError, match="only available during a Celery task execution"):
        wireup_celery.get_task_container()
