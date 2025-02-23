import unittest
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typing_extensions import Annotated
from wireup import Inject
from wireup.decorators import make_inject_decorator
from wireup.errors import UnknownOverrideRequestedError
from wireup.ioc.override_manager import OverrideManager
from wireup.ioc.types import Qualifier, ServiceOverride

from test.conftest import Container
from test.fixtures import FooBar, FooBase, FooBaz
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.util import run


async def test_container_overrides_deps_service_locator(container: Container):
    container._registry.register(RandomService)

    random_mock = MagicMock()
    random_mock.get_random.return_value = 5

    with container.override.service(target=RandomService, new=random_mock):
        svc = await run(container.get(RandomService))
        assert svc.get_random() == 5

    random_mock.get_random.assert_called_once()
    assert (await run(container.get(RandomService))).get_random() == 4


async def test_container_overrides_deps_service_locator_interface(container: Container):
    container._registry.register_abstract(FooBase)
    container._registry.register(FooBar)

    foo_mock = MagicMock()
    foo_mock.foo = "mock"

    with container.override.service(target=FooBase, new=foo_mock):
        svc = await run(container.get(FooBase))
        assert svc.foo == "mock"


async def test_container_override_many_with_qualifier(container: Container):
    container._registry.register(RandomService, qualifier="Rand1")
    container._registry.register(RandomService, qualifier="Rand2")

    @make_inject_decorator(container)
    def target(
        rand1: Annotated[RandomService, Inject(qualifier="Rand1")],
        rand2: Annotated[RandomService, Inject(qualifier="Rand2")],
    ):
        assert rand1.get_random() == 5
        assert rand2.get_random() == 6

        assert isinstance(rand1, MagicMock)
        assert isinstance(rand2, MagicMock)

    rand1_mock = MagicMock()
    rand1_mock.get_random.return_value = 5

    rand2_mock = MagicMock()
    rand2_mock.get_random.return_value = 6

    overrides = [
        ServiceOverride(target=RandomService, qualifier="Rand1", new=rand1_mock),
        ServiceOverride(target=RandomService, qualifier="Rand2", new=rand2_mock),
    ]
    with container.override.services(overrides=overrides):
        target()

    rand1_mock.get_random.assert_called_once()
    rand2_mock.get_random.assert_called_once()


async def test_container_override_with_interface(container: Container):
    container._registry.register_abstract(FooBase)
    container._registry.register(FooBar)

    @make_inject_decorator(container)
    async def target(foo: FooBase):
        assert foo.foo == "mock"
        assert isinstance(foo, MagicMock)

    foo_mock = MagicMock()

    with patch.object(foo_mock, "foo", new="mock"):
        with container.override.service(target=FooBase, new=foo_mock):
            svc = await run(container.get(FooBase))
            assert svc.foo == "mock"

            target()


async def test_clear_services_removes_all():
    overrides: dict[tuple[type, Qualifier], Any] = {}
    mock1 = MagicMock()
    override_mgr = OverrideManager(overrides, lambda _klass, _qualifier: True)
    override_mgr.set(RandomService, new=mock1)
    assert overrides == {(RandomService, None): mock1}

    override_mgr.clear()
    assert overrides == {}


async def test_raises_on_unknown_override(container: Container):
    with pytest.raises(
        UnknownOverrideRequestedError,
        match="Cannot override unknown <class 'unittest.case.TestCase'> with qualifier 'foo'.",
    ):
        with container.override.service(target=unittest.TestCase, qualifier="foo", new=MagicMock()):
            pass


async def test_override_interface_works_with_service_locator(container: Container):
    container._registry.register_abstract(FooBase)
    container._registry.register(FooBar)

    foobaz = FooBaz()

    assert (await run(container.get(FooBase))).foo == "bar"

    with container.override.service(FooBase, new=foobaz):
        assert (await run(container.get(FooBase))).foo == "baz"
