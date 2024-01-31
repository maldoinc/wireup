from test.fixtures import Counter, FooBar, FooBase
from test.services.no_annotations.random.random_service import RandomService
from unittest import TestCase

from wireup import DependencyContainer, ParameterBag, ServiceLifetime, warmup_container, wire
from wireup.errors import (
    DuplicateServiceRegistrationError,
    FactoryDuplicateServiceRegistrationError,
    FactoryReturnTypeIsEmptyError,
)


class ThingToBeCreated:
    def __init__(self, val: str):
        self.val = val


class TestContainerStaticFactory(TestCase):
    def setUp(self) -> None:
        self.container = DependencyContainer(ParameterBag())

    def test_injects_using_factory_with_dependencies(self):
        self.container.register(RandomService)
        self.container.params.put("dummy_val", "foo")

        @self.container.register
        def create_thing(val=wire(param="dummy_val")) -> ThingToBeCreated:
            return ThingToBeCreated(val=val)

        @self.container.autowire
        def inner(thing: ThingToBeCreated):
            self.assertEqual(thing.val, "foo")

        inner()

        self.assertEqual(create_thing("new").val, "new", msg="Assert fn is not modified")

    def test_injects_using_factory_returns_singletons(self):
        self.container.params.put("start", 5)

        @self.container.register
        def create_thing(start=wire(param="start")) -> Counter:
            return Counter(count=start)

        @self.container.autowire
        def inner(c1: Counter, c2: Counter):
            c1.inc()

            self.assertEqual(c1.count, 6)
            self.assertEqual(c1.count, c2.count)

        inner()

    def test_injects_using_factory_returns_unique_instances(self):
        self.container.params.put("start", 5)

        @self.container.register(lifetime=ServiceLifetime.TRANSIENT)
        def create_thing(start=wire(param="start")) -> Counter:
            return Counter(count=start)

        @self.container.autowire
        def inner(c1: Counter, c2: Counter):
            c1.inc()

            self.assertEqual(c1.count, 6)
            self.assertNotEqual(c1.count, c2.count)
            self.assertEqual(c2.count, 5)

        inner()
        inner()

    def test_injects_on_instance_methods(self):
        this = self

        class Dummy:
            @self.container.autowire
            def inner(self, c1: Counter):
                c1.inc()
                this.assertEqual(c1.count, 1)

        @self.container.register
        def create_thing() -> Counter:
            return Counter()

        Dummy().inner()

    def test_register_known_container_type(self):
        self.container.register(RandomService)

        with self.assertRaises(DuplicateServiceRegistrationError) as context:

            @self.container.register
            def create_random_service() -> RandomService:
                return RandomService()

        self.assertEqual(
            f"Cannot register type {RandomService} with qualifier 'None' as it already exists.",
            str(context.exception),
        )

    def test_register_factory_known_type_from_other_factory(self):
        with self.assertRaises(FactoryDuplicateServiceRegistrationError) as context:

            @self.container.register
            def create_random_service() -> RandomService:
                return RandomService()

            @self.container.register
            def create_random_service_too() -> RandomService:
                return RandomService()

        self.assertEqual(
            f"A function is already registered as a factory for dependency type {RandomService} with qualifier None.",
            str(context.exception),
        )

    def test_register_factory_no_return_type(self):
        with self.assertRaises(FactoryReturnTypeIsEmptyError) as context:

            @self.container.register
            def create_random_service():
                return RandomService()

        self.assertEqual(
            "Factory functions must specify a return type denoting the type of dependency it can create.",
            str(context.exception),
        )

    def test_factory_as_property_accessor(self):
        @self.container.register
        class FooGenerator:
            def get_foo(self) -> FooBar:
                return FooBar()

        @self.container.autowire
        def inner(foobar: FooBar):
            self.assertEqual(foobar.foo, "bar")

        @self.container.register
        def foo_factory(foo_gen: FooGenerator) -> FooBar:
            return foo_gen.get_foo()

        inner()

    def test_factory_abstract_type(self):
        self.container.register(FooBar)

        @self.container.autowire
        def inner(foo: FooBase):
            self.assertEqual(foo.foo, "bar")

        @self.container.register
        def foo_factory() -> FooBase:
            return FooBar()

        inner()

    def test_factory_does_warmup_wires_real_object(self):
        @self.container.autowire
        def inner(foo: FooBar):
            self.assertIsInstance(foo, FooBar)
            self.assertEqual(foo.foo, "bar")

        @self.container.register
        def foo_factory() -> FooBar:
            return FooBar()

        warmup_container(self.container, service_modules=[])
        inner()

    def test_factory_does_warmup_wires_real_object_from_factory(self):
        @self.container.autowire
        def inner(foo: FooBase):
            self.assertIsInstance(foo, FooBase)
            self.assertEqual(foo.foo, "bar")

        @self.container.register
        def foo_factory() -> FooBase:
            return FooBar()

        warmup_container(self.container, service_modules=[])
        inner()

    def test_factory_allow_registering_with_qualifier(self):
        self.container.register(FooBar)

        @self.container.register(qualifier="1")
        def foo_factory() -> FooBar:
            return FooBar()

        @self.container.register(qualifier="2")
        def foo_factory2() -> FooBar:
            return FooBar()

        self.assertTrue(self.container.get(FooBar))
        self.assertTrue(self.container.get(FooBar, "1"))
        self.assertTrue(self.container.get(FooBar, "2"))
