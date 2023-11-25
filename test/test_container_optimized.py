import unittest
from dataclasses import dataclass
from test.fixtures import FooBar, FooBase, FooBaz
from test.services.no_annotations.random.random_service import RandomService

from typing_extensions import Annotated
from wireup import DependencyContainer, ParameterBag, ServiceLifetime, Wire


@dataclass
class SomeService:
    start: Annotated[int, Wire(param="start")]
    random: RandomService


class TestContainerCompiled(unittest.TestCase):
    def setUp(self):
        self.container = DependencyContainer(ParameterBag())
        self.container.register(SomeService)
        self.container.register(RandomService)
        self.container.params.put("start", 10)

    def test_compiled_does_not_return_proxies(self):
        self.container.warmup()

        service = self.container.get(SomeService)
        self.assertIsInstance(service, SomeService)
        self.assertIsInstance(service.random, RandomService)
        self.assertEqual(service.start, 10)

    def test_compiled_works_with_interfaces(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar)
        self.container.warmup()

        @self.container.autowire
        def target(foo: FooBase):
            self.assertEqual(foo.foo, "bar")

        target()

    def test_compiled_works_with_interfaces_and_qualifiers(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="bar")
        self.container.register(FooBaz, qualifier="baz")
        self.container.warmup()

        @self.container.autowire
        def target(bar: Annotated[FooBase, Wire(qualifier="bar")], baz: Annotated[FooBase, Wire(qualifier="baz")]):
            self.assertEqual(bar.foo, "bar")
            self.assertEqual(baz.foo, "baz")

        target()

    def test_compiled_works_with_interfaces_and_qualifiers_on_dependencies(self):
        @self.container.register
        @dataclass
        class Thing:
            foo: Annotated[FooBase, Wire(qualifier="bar")]

        @self.container.register
        @dataclass
        class Thing2:
            thing: Thing

        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="bar")
        self.container.register(FooBaz, qualifier="baz")
        self.container.warmup()

        @self.container.autowire
        def target(thing2: Thing2):
            self.assertEqual(thing2.thing.foo.foo, "bar")

        target()

    def test_compiled_injecting_interface_injects_real_instantiated_impl_object(self):
        @self.container.register
        @dataclass
        class Thing:
            foo: FooBase

        @self.container.register
        @dataclass
        class Thing2:
            thing: Thing

        self.container.abstract(FooBase)
        self.container.register(FooBar)
        self.container.warmup()

        @self.container.autowire
        def target(thing2: Thing2):
            self.assertIsInstance(thing2, Thing2)
            self.assertIsInstance(thing2.thing, Thing)
            self.assertIsInstance(thing2.thing.foo, FooBar)

            self.assertEqual(thing2.thing.foo.foo, "bar")

        target()

    def test_compiled_injecting_interface_injects_real_instantiated_impl_object_directly(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier=FooBar)
        self.container.warmup()

        @self.container.autowire
        def target(foo: Annotated[FooBase, Wire(qualifier=FooBar)]):
            self.assertEqual(foo.foo, "bar")

        target()

    def test_compiled_injecting_interface_locates_real_instantiated_impl_object_directly(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar)
        self.container.warmup()

        self.assertIsInstance(self.container.get(FooBase), FooBar)

    def test_compiled_works_with_interfaces_and_qualifiers_uses_transient_deps(self):
        base_called = False
        transient_called = False

        @self.container.register
        class Base:
            def __init__(self):
                nonlocal base_called
                base_called = True

        @self.container.register(lifetime=ServiceLifetime.TRANSIENT)
        @dataclass
        class Transient:
            base: Base

            def __init__(self):
                nonlocal transient_called
                transient_called = True

        self.container.warmup()
        self.assertTrue(base_called)
        self.assertFalse(transient_called)
