import unittest

from test.fixtures import FooBase, FooBar
from unittest.mock import MagicMock, patch

from typing_extensions import Annotated

from test.unit.services.no_annotations.random.random_service import RandomService
from wireup import DependencyContainer, ParameterBag, Wire
from wireup.errors import UnknownOverrideRequestedError
from wireup.ioc.override_manager import OverrideManager
from wireup.ioc.types import ServiceOverride


class TestContainerOverride(unittest.TestCase):
    def setUp(self) -> None:
        self.container = DependencyContainer(ParameterBag())

    def test_container_overrides_deps_service_locator(self):
        self.container.register(RandomService)

        random_mock = MagicMock()
        random_mock.get_random.return_value = 5

        with self.container.override.service(target=RandomService, new=random_mock):
            svc = self.container.get(RandomService)
            self.assertEqual(svc.get_random(), 5)

        random_mock.get_random.assert_called_once()
        self.assertEqual(self.container.get(RandomService).get_random(), 4)

    def test_container_overrides_deps_service_locator_interface(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar)

        foo_mock = MagicMock()
        foo_mock.foo = "mock"

        with self.container.override.service(target=FooBase, new=foo_mock):
            svc = self.container.get(FooBase)
            self.assertEqual(svc.foo, "mock")

    def test_container_override_many_with_qualifier(self):
        self.container.register(RandomService, qualifier="Rand1")
        self.container.register(RandomService, qualifier="Rand2")

        @self.container.autowire
        def target(
            rand1: Annotated[RandomService, Wire(qualifier="Rand1")],
            rand2: Annotated[RandomService, Wire(qualifier="Rand2")],
        ):
            self.assertEqual(rand1.get_random(), 5)
            self.assertEqual(rand2.get_random(), 6)

            self.assertIsInstance(rand1, MagicMock)
            self.assertIsInstance(rand2, MagicMock)

        rand1_mock = MagicMock()
        rand1_mock.get_random.return_value = 5

        rand2_mock = MagicMock()
        rand2_mock.get_random.return_value = 6

        overrides = [
            ServiceOverride(target=RandomService, qualifier="Rand1", new=rand1_mock),
            ServiceOverride(target=RandomService, qualifier="Rand2", new=rand2_mock),
        ]
        with self.container.override.services(overrides=overrides):
            target()

        rand1_mock.get_random.assert_called_once()
        rand2_mock.get_random.assert_called_once()

    def test_container_override_with_interface(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar)

        @self.container.autowire
        def target(foo: FooBase):
            self.assertEqual(foo.foo, "mock")
            self.assertIsInstance(foo, MagicMock)

        foo_mock = MagicMock()

        with patch.object(foo_mock, "foo", new="mock"):
            with self.container.override.service(target=FooBase, new=foo_mock):
                svc = self.container.get(FooBase)
                self.assertEqual(svc.foo, "mock")

                target()

    def test_clear_services_removes_all(self):
        overrides = {}
        mock1 = MagicMock()
        override_mgr = OverrideManager(overrides, lambda _klass, _qualifier: True)
        override_mgr.set(RandomService, new=mock1)
        self.assertEqual(overrides, {(RandomService, None): mock1})

        override_mgr.clear()
        self.assertEqual(overrides, {})

    def test_raises_on_unknown_override(self):
        with self.assertRaises(UnknownOverrideRequestedError) as e:
            with self.container.override.service(target=unittest.TestCase, qualifier="foo", new=MagicMock()):
                pass

        self.assertEqual(
            str(e.exception), "Cannot override unknown <class 'unittest.case.TestCase'> with qualifier 'foo'."
        )
