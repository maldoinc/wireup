import unittest
from test.unit.services.no_annotations.random.random_service import RandomService

from typing_extensions import Annotated
from wireup import Inject, ServiceLifetime, Wire
from wireup.errors import (
    DuplicateServiceRegistrationError,
    FactoryDuplicateServiceRegistrationError,
    FactoryReturnTypeIsEmptyError,
)
from wireup.ioc.service_registry import ServiceRegistry
from wireup.ioc.types import AnnotatedParameter, ParameterWrapper


class TestServiceRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = ServiceRegistry()

    def test_register_service(self):
        self.registry.register_service(MyService, qualifier="default", lifetime=ServiceLifetime.SINGLETON)

        # Check if the service is registered correctly
        self.assertTrue(self.registry.is_impl_known(MyService))
        self.assertTrue(self.registry.is_impl_with_qualifier_known(MyService, "default"))
        self.assertTrue(self.registry.is_type_with_qualifier_known(MyService, "default"))
        self.assertTrue(self.registry.is_impl_singleton(MyService))

        # Test registering a duplicate service
        with self.assertRaises(DuplicateServiceRegistrationError):
            self.registry.register_service(MyService, qualifier="default", lifetime=ServiceLifetime.SINGLETON)

    def test_register_abstract(self):
        self.registry.register_abstract(MyInterface)

        # Check if the interface is registered correctly
        self.assertTrue(self.registry.is_interface_known(MyInterface))

    def test_register_factory(self):
        self.registry.register_factory(my_factory, lifetime=ServiceLifetime.SINGLETON)

        # Check if the factory function is registered correctly
        self.assertTrue(self.registry.is_impl_known_from_factory(RandomService, None))

        # Test registering a factory function with missing return type
        def invalid_factory():
            pass

        with self.assertRaises(FactoryReturnTypeIsEmptyError):
            self.registry.register_factory(invalid_factory, lifetime=ServiceLifetime.SINGLETON)

        # Test registering a duplicate factory function
        with self.assertRaises(FactoryDuplicateServiceRegistrationError):
            self.registry.register_factory(my_factory, lifetime=ServiceLifetime.SINGLETON)

    def test_is_impl_known(self):
        self.assertFalse(self.registry.is_impl_known(MyService))

        self.registry.register_service(MyService, qualifier="default", lifetime=ServiceLifetime.SINGLETON)
        self.assertTrue(self.registry.is_impl_known(MyService))

    def test_is_impl_with_qualifier_known(self):
        self.assertFalse(self.registry.is_impl_with_qualifier_known(MyService, "default"))

        self.registry.register_service(MyService, qualifier="default", lifetime=ServiceLifetime.SINGLETON)
        self.assertTrue(self.registry.is_impl_with_qualifier_known(MyService, "default"))

    def test_is_type_with_qualifier_known(self):
        self.assertFalse(self.registry.is_type_with_qualifier_known(MyService, "default"))

        self.registry.register_service(MyService, qualifier="default", lifetime=ServiceLifetime.SINGLETON)
        self.assertTrue(self.registry.is_type_with_qualifier_known(MyService, "default"))

    def test_is_impl_known_from_factory(self):
        self.assertFalse(self.registry.is_impl_known_from_factory(str, None))

        self.registry.register_factory(my_factory, lifetime=ServiceLifetime.SINGLETON)
        self.assertTrue(self.registry.is_impl_known_from_factory(RandomService, None))

    def test_is_impl_singleton(self):
        self.assertFalse(self.registry.is_impl_singleton(MyService))

        self.registry.register_service(MyService, qualifier="default", lifetime=ServiceLifetime.SINGLETON)
        self.assertTrue(self.registry.is_impl_singleton(MyService))

    def test_is_interface_known(self):
        self.assertFalse(self.registry.is_interface_known(MyInterface))

        self.registry.register_abstract(MyInterface)
        self.assertTrue(self.registry.is_interface_known(MyInterface))

    def test_register_only_injectable_params(self):
        def target(_a, _b, _c, _d: RandomService, _e: str, _f: Annotated[str, Inject(param="name")]): ...

        self.registry.target_init_context(target)
        self.assertEqual(
            self.registry.context.dependencies[target],
            {
                "_d": AnnotatedParameter(klass=RandomService),
                "_f": AnnotatedParameter(klass=str, annotation=ParameterWrapper("name")),
            },
        )


class MyService:
    pass


class MyInterface:
    pass


def my_factory() -> RandomService:
    return RandomService()
