import unittest
from unittest.mock import MagicMock

import pytest
import wireup
from wireup._annotations import Injected
from wireup.errors import UnknownOverrideRequestedError
from wireup.ioc.types import InjectableOverride

from test.conftest import Container
from test.unit.services.abstract_multiple_bases import FooBar
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.with_annotations.services import (
    Foo,
    FooImpl,
    ScopedService,
    TransientService,
    random_service_factory,
)
from test.unit.util import run


def test_container_overrides_deps_service_locator(container: Container):
    container = wireup.create_sync_container(services=[random_service_factory])

    random_mock = MagicMock()
    random_mock.get_random.return_value = 5

    with container.override.injectable(target=RandomService, qualifier="foo", new=random_mock):
        svc = container.get(RandomService, qualifier="foo")
        assert svc.get_random() == 5

    random_mock.get_random.assert_called_once()
    assert container.get(RandomService, qualifier="foo").get_random() == 4


async def test_container_overrides_deps_service_locator_interface():
    container = wireup.create_sync_container(services=[Foo, FooImpl])

    foo_mock = MagicMock()
    foo_mock.get_foo.return_value = "mock"

    with container.override.injectable(target=Foo, new=foo_mock):
        svc = await run(container.get(Foo))
        assert svc.get_foo() == "mock"

    res = await run(container.get(Foo))
    assert res.get_foo() == "foo"


async def test_container_override_many_with_qualifier(container: Container):
    rand1_mock = MagicMock()
    rand2_mock = MagicMock()

    overrides = [
        InjectableOverride(target=ScopedService, new=rand1_mock),
        InjectableOverride(target=TransientService, new=rand2_mock),
    ]

    @wireup.inject_from_container(container)
    def target(scoped: Injected[ScopedService], transient: Injected[TransientService]) -> None:
        assert scoped is rand1_mock
        assert transient is rand2_mock

    with container.override.services(overrides=overrides):
        target()


async def test_raises_on_unknown_override(container: Container):
    with pytest.raises(
        UnknownOverrideRequestedError,
        match="Cannot override unknown <class 'unittest.case.TestCase'> with qualifier 'foo'.",
    ):
        with container.override.injectable(target=unittest.TestCase, qualifier="foo", new=MagicMock()):
            pass


async def test_overrides_async_dependency() -> None:
    @wireup.injectable
    async def async_foo_factory() -> FooBar:
        return FooBar()

    container = wireup.create_async_container(services=[async_foo_factory])

    foo_mock = MagicMock()
    foo_mock.foo = "mock"

    with container.override.injectable(target=FooBar, new=foo_mock):
        svc = await container.get(FooBar)
        assert svc.foo == "mock"

    res = await container.get(FooBar)
    assert res.foo == "bar"
