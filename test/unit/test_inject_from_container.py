import re
from typing import Optional

import pytest
import wireup
from typing_extensions import Annotated
from wireup import Inject, inject_from_container
from wireup._annotations import Injected
from wireup.errors import WireupError

from test.conftest import Container
from test.unit import services
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.with_annotations.services import Foo, FooImpl, OtherFooImpl, random_service_factory


async def test_injects_targets(container: Container) -> None:
    class NotManagedByWireup: ...

    @inject_from_container(container)
    def target(
        foo: Injected[Foo],
        other_foo: Annotated[Foo, Inject(qualifier="other")],
        random_service: Annotated[RandomService, Inject(qualifier="foo")],
        env_name: Annotated[str, Inject(param="env_name")],
        env_env: Annotated[str, Inject(expr="${env_name}-${env_name}")],
        not_managed_by_wireup: NotManagedByWireup,
    ) -> None:
        assert isinstance(foo, Foo)
        assert isinstance(foo, FooImpl)

        assert isinstance(other_foo, Foo)
        assert isinstance(other_foo, OtherFooImpl)

        assert random_service.get_random() == 4
        assert env_name == "test"
        assert env_env == "test-test"
        assert isinstance(not_managed_by_wireup, NotManagedByWireup)

    target(not_managed_by_wireup=NotManagedByWireup())


async def test_injects_targets_async() -> None:
    container = wireup.create_async_container(service_modules=[services], parameters={"env_name": "test"})

    class NotManagedByWireup: ...

    @inject_from_container(container)
    def target(
        foo: Injected[Foo],
        other_foo: Annotated[Foo, Inject(qualifier="other")],
        random_service: Annotated[RandomService, Inject(qualifier="foo")],
        env_name: Annotated[str, Inject(param="env_name")],
        env_env: Annotated[str, Inject(expr="${env_name}-${env_name}")],
        not_managed_by_wireup: NotManagedByWireup,
    ) -> None:
        assert isinstance(foo, Foo)
        assert isinstance(foo, FooImpl)

        assert isinstance(other_foo, Foo)
        assert isinstance(other_foo, OtherFooImpl)

        assert random_service.get_random() == 4
        assert env_name == "test"
        assert env_env == "test-test"
        assert isinstance(not_managed_by_wireup, NotManagedByWireup)

    @inject_from_container(container)
    async def async_target(
        foo: Injected[Foo],
        other_foo: Annotated[Foo, Inject(qualifier="other")],
        random_service: Annotated[RandomService, Inject(qualifier="foo")],
        env_name: Annotated[str, Inject(param="env_name")],
        env_env: Annotated[str, Inject(expr="${env_name}-${env_name}")],
        not_managed_by_wireup: NotManagedByWireup,
    ) -> None:
        assert isinstance(foo, Foo)
        assert isinstance(foo, FooImpl)

        assert isinstance(other_foo, Foo)
        assert isinstance(other_foo, OtherFooImpl)

        assert random_service.get_random() == 4
        assert env_name == "test"
        assert env_env == "test-test"
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


def test_autowire_supports_multiple_containers_does_not_patch_function():
    c1 = wireup.create_sync_container(service_modules=[services], parameters={"env_name": "test"})
    c2 = wireup.create_sync_container(service_modules=[services], parameters={"env_name": "test"})

    def inner(foo: Annotated[Foo, Inject()], p1: Annotated[str, Inject(param="env_name")]):
        assert isinstance(foo, Foo)
        assert p1 == "test"

    inject_from_container(c1)(inner)()
    inject_from_container(c2)(inner)()


def test_container_overrides_passed_parameters():
    c1 = wireup.create_sync_container(service_modules=[services], parameters={"env_name": "test"})

    def inner(foo: Annotated[Foo, Inject()], p1: Annotated[str, Inject(param="env_name")]):
        assert isinstance(foo, Foo)
        assert p1 == "test"

    inject_from_container(c1)(inner)(p1="bar")


def test_container_wires_none_values_from_parameter_bag():
    container = wireup.create_async_container(parameters={"foo": None})

    @inject_from_container(container)
    def inner(name: Annotated[str, Inject(param="foo")], name2: Annotated[str, Inject(param="foo")]):
        assert name is None
        assert name2 is None

    inner()


def test_injects_ctor():
    container = wireup.create_async_container(services=[random_service_factory], parameters={"env": "test"})

    class Dummy:
        @inject_from_container(container)
        def __init__(
            self,
            rand_service: Annotated[RandomService, Inject(qualifier="foo")],
            env: Annotated[str, Inject(param="env")],
        ):
            self.env = env
            self.rand_service = rand_service

        def do_thing(self):
            return f"Running in {self.env} with a result of {self.rand_service.get_random()}"

    dummy = Dummy()
    assert dummy.do_thing() == "Running in test with a result of 4"


def test_inject_from_container_handles_optionals() -> None:
    class MaybeThing: ...

    def make_maybe_thing() -> Optional[MaybeThing]:
        return None

    class Thing: ...

    def make_thing(_thing2: Optional[MaybeThing]) -> Thing:
        return Thing()

    container = wireup.create_sync_container(services=[wireup.service(make_maybe_thing), wireup.service(make_thing)])

    @wireup.inject_from_container(container)
    def main(maybe_thing: Injected[Optional[MaybeThing]], thing: Injected[Thing]):
        assert maybe_thing is None
        assert isinstance(thing, Thing)

    main()
