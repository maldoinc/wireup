import re

import pytest
import wireup
from typing_extensions import Annotated
from wireup import Inject, inject_from_container
from wireup.errors import WireupError

from test.conftest import Container
from test.unit import services
from test.unit.services.no_annotations.random.random_service import RandomService


async def test_injects_targets(container: Container) -> None:
    class NotManagedByWireup: ...

    @inject_from_container(container)
    def target(
        random_service: Annotated[RandomService, Inject(qualifier="foo")],
        env_name: Annotated[str, Inject(param="env_name")],
        env_env: Annotated[str, Inject(expr="${env_name}-${env_name}")],
        not_managed_by_wireup: NotManagedByWireup,
    ) -> None:
        assert random_service.get_random() == 4
        assert env_name == "test"
        assert env_env == "test-test"
        assert isinstance(not_managed_by_wireup, NotManagedByWireup)

    target(not_managed_by_wireup=NotManagedByWireup())


async def test_injects_targets2() -> None:
    container = wireup.create_async_container(service_modules=[services], parameters={"env_name": "test"})

    class NotManagedByWireup: ...

    @inject_from_container(container)
    def target(
        random_service: Annotated[RandomService, Inject(qualifier="foo")],
        env_name: Annotated[str, Inject(param="env_name")],
        not_managed_by_wireup: NotManagedByWireup,
    ) -> None:
        assert random_service.get_random() == 4
        assert env_name == "test"
        assert isinstance(not_managed_by_wireup, NotManagedByWireup)

    @inject_from_container(container)
    async def async_target(
        random_service: Annotated[RandomService, Inject(qualifier="foo")],
        env_name: Annotated[str, Inject(param="env_name")],
        not_managed_by_wireup: NotManagedByWireup,
    ) -> None:
        assert random_service.get_random() == 4
        assert env_name == "test"
        assert isinstance(not_managed_by_wireup, NotManagedByWireup)

    target(not_managed_by_wireup=NotManagedByWireup())
    await async_target(not_managed_by_wireup=NotManagedByWireup())


@pytest.mark.parametrize("qualifier", [None, "foo"])
async def test_raises_on_unknown_service(container: Container, qualifier: str) -> None:
    class NotManagedByWireup: ...

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'not_managed_by_wireup' of Function test.unit.test_inject_from_container._ "
            "depends on an unknown service Type test.unit.test_inject_from_container.NotManagedByWireup "
            f"with qualifier {qualifier}."
        ),
    ):

        @inject_from_container(container)
        def _(
            not_managed_by_wireup: Annotated[NotManagedByWireup, Inject(qualifier=qualifier)],
        ) -> None: ...


async def test_raises_on_unknown_parameter(container: Container) -> None:
    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'not_managed_by_wireup' of Function test.unit.test_inject_from_container._ "
            "depends on an unknown Wireup parameter 'invalid'."
        ),
    ):

        @inject_from_container(container)
        def _(
            not_managed_by_wireup: Annotated[str, Inject(param="invalid")],
        ) -> None: ...


async def test_injects_service_with_provided_async_scoped_container() -> None:
    container = wireup.create_async_container(service_modules=[services], parameters={"env_name": "test"})

    async with container.enter_scope() as scoped:

        @inject_from_container(container, lambda: scoped)
        def target(rand_service: Annotated[RandomService, Inject(qualifier="foo")]) -> None:
            assert isinstance(rand_service, RandomService)

    target()


async def test_container_sync_raises_async_def() -> None:
    container = wireup.create_sync_container(service_modules=[services], parameters={"env_name": "test"})

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Sync container cannot perform injection on async targets. "
            "Create an async container via wireup.create_async_container."
        ),
    ):

        @inject_from_container(container)
        async def _(rand_service: Annotated[RandomService, Inject(qualifier="foo")]) -> None:
            assert isinstance(rand_service, RandomService)
