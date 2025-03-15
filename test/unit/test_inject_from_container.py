import wireup
from typing_extensions import Annotated
from wireup._decorators import inject_from_container
from wireup.annotation import Inject

from test.conftest import Container
from test.unit import services
from test.unit.services.no_annotations.random.random_service import RandomService


async def test_inject_from_container_injects_targets(container: Container) -> None:
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

    target(not_managed_by_wireup=NotManagedByWireup())


async def test_inject_from_container_injects_targets2() -> None:
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
