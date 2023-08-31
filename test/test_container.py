import unittest
from dataclasses import dataclass
from unittest.mock import Mock, patch

import examples.services
from examples.services.random_service import RandomService
from examples.services.truly_random_service import TrulyRandomService
from test.fixtures import Counter, FooBase, FooBar, FooBaz
from wireup import wire
from wireup.ioc.container_util import ParameterWrapper
from wireup.ioc.dependency_container import ContainerProxy, DependencyContainer
from wireup.ioc.parameter import ParameterBag, TemplatedString
from wireup.ioc.util import find_classes_in_module


class TestContainer(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.container = DependencyContainer(ParameterBag())
        self.container.register_all_in_module(examples.services)

    def test_works_simple_get_instance(self):
        rand = self.container.get(RandomService)

        assert isinstance(rand, ContainerProxy), "Assert that we never interact directly with the instantiated classes"
        self.assertEqual(rand.get_random(), 4, "Assert that proxy pass-through works")

    def test_raises_on_unknown_dependency(self):
        class UnknownDep:
            ...

        self.assertRaises(ValueError, lambda: self.container.get(UnknownDep))

    def test_container_returns_singletons(self):
        self.container.register(Counter)
        c1 = self.container.get(Counter)
        c1.inc()

        self.assertEqual(c1.count, self.container.get(Counter).count)

    def test_works_simple_get_instance_with_other_service_injected(self):
        truly_random = self.container.get(TrulyRandomService)

        assert isinstance(truly_random, ContainerProxy)
        self.assertEqual(truly_random.get_truly_random(), 5)

    def test_get_class_with_param_bindings(self) -> None:
        @self.container.register
        class ServiceWithParams:
            def __init__(
                self,
                connection_str: str = wire(param="connection_str"),
                cache_dir: str = wire(expr="${cache_dir}/etc"),
            ) -> None:
                self.connection_str = connection_str
                self.cache_dir = cache_dir

        self.container.params.put("connection_str", "sqlite://memory")
        self.container.params.put("cache_dir", "/var/cache")
        svc = self.container.get(ServiceWithParams)

        self.assertEqual(svc.connection_str, "sqlite://memory")
        self.assertEqual(svc.cache_dir, "/var/cache/etc")

    def test_inject_param(self):
        result = wire(param="value")
        assert isinstance(result, ParameterWrapper)
        self.assertEqual(result.param, "value")

    def test_inject_expr(self):
        result = wire(expr="some ${param}")
        assert isinstance(result, ParameterWrapper)
        assert isinstance(result.param, TemplatedString)
        self.assertEqual(result.param.value, "some ${param}")

    @patch("importlib.import_module")
    def test_inject_fastapi_dep(self, mock_import_module):
        mock_import_module.return_value = Mock(Depends=Mock())
        result = wire()
        self.assertEqual(result, mock_import_module.return_value.Depends.return_value)
        mock_import_module.assert_called_once_with("fastapi")

    @patch("importlib.import_module", side_effect=ModuleNotFoundError)
    def test_inject_missing_fastapi(self, _):
        with self.assertRaises(Exception) as context:
            wire()

        assert "One of param, expr or qualifier must be set" in str(context.exception)

    def test_register_known_class(self):
        class TestRegisterKnown:
            pass

        self.container.register(TestRegisterKnown)
        with self.assertRaises(ValueError) as context:
            self.container.register(TestRegisterKnown)

        self.assertIn(
            "Cannot register type "
            "<class 'test_container.TestContainer.test_register_known_class.<locals>.TestRegisterKnown'> "
            "with qualifier 'None' as it already exists.",
            str(context.exception),
        )

    def test_autowire_sync(self):
        self.container.params.put("env", "test")

        def test_function(random: TrulyRandomService, env: str = wire(param="env")) -> int:
            self.assertEqual(env, "test")
            return random.get_truly_random()

        autowired_fn = self.container.autowire(test_function)
        assert callable(autowired_fn)
        self.assertEqual(autowired_fn(), 5)

    async def test_autowire_async(self):
        self.container.params.put("env", "test")

        async def test_function(random: RandomService, env: str = wire(param="env")) -> int:
            self.assertEqual(env, "test")
            return random.get_random()

        autowired_fn = self.container.autowire(test_function)
        assert callable(autowired_fn)
        self.assertEqual(await autowired_fn(), 4)

    def test_register_all_in_module(self):
        # These classes are registered in setup
        for c in find_classes_in_module(examples.services):
            assert isinstance(self.container.get(c), ContainerProxy)

    def test_get_unknown_class(self):
        class TestGetUnknown:
            pass

        with self.assertRaises(ValueError) as context:
            self.container.get(TestGetUnknown)

        assert f"Cannot wire unknown class {TestGetUnknown}." in str(context.exception)

    def test_can_initialize_from_context_tests_add_update(self):
        @dataclass
        class NoHints:
            interpolated: str
            env: str
            mambo_number: int

        self.container.initialization_context.add_param(NoHints, "interpolated", TemplatedString("${first}-${second}"))
        self.container.initialization_context.update(NoHints, {"mambo_number": "mambo_number", "env": "env"})

        self.container.register(NoHints)
        self.container.params.update({"first": "foo", "second": "bar", "env": "test", "mambo_number": 5})
        obj = self.container.get(NoHints)

        self.assertEqual(obj.interpolated, "foo-bar")
        self.assertEqual(obj.env, "test")
        self.assertEqual(obj.mambo_number, 5)

    def test_db_service_dataclass_with_params(self):
        @dataclass
        class MyDbService:
            connection_str: str = wire(param="connection_str")
            cache_dir: str = wire(expr="${cache_dir}/${auth.user}/db")

        self.container = DependencyContainer(ParameterBag())
        self.container.register(MyDbService)
        self.container.params.update(
            {"cache_dir": "/var/cache", "connection_str": "sqlite://memory", "auth.user": "anon"},
        )

        db = self.container.get(MyDbService)

        self.assertEqual(db.cache_dir, "/var/cache/anon/db")
        self.assertEqual(db.connection_str, "sqlite://memory")

    def test_locates_service_with_qualifier(self):
        self.container.register(Counter, qualifier="foo_qualified")
        resolved = self.container.get(Counter, qualifier="foo_qualified")
        self.assertEqual(resolved.count, 0)
        resolved.inc()
        self.assertEqual(resolved.count, 1)

    def test_raises_when_not_supplying_qualifier_registered_multiple(self):
        self.container.register(Counter, qualifier="foo_qualified")
        self.container.register(Counter, qualifier="foo_qualified2")

        with self.assertRaises(ValueError) as context:
            self.container.get(Counter)

        self.assertEqual(
            "Cannot wire unknown class <class 'test.fixtures.Counter'>. "
            "Use @Container.{register,abstract} to enable autowiring",
            str(context.exception),
        )

    def test_two_qualifiers_are_injected(self):
        @self.container.autowire
        def inner(sub1: FooBase = wire(qualifier="sub1"), sub2: FooBase = wire(qualifier="sub2")):
            self.assertEqual(sub1.foo, "bar")
            self.assertEqual(sub2.foo, "baz")

        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="sub1")
        self.container.register(FooBaz, qualifier="sub2")
        inner()

    def test_get_with_interface_and_qualifier(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="sub1")

        foo = self.container.get(FooBase, qualifier="sub1")
        self.assertEqual(foo.foo, "bar")

    def test_register_twice_should_raise(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="foo")

        with self.assertRaises(ValueError) as context:
            self.container.register(FooBar, qualifier="foo")

        self.assertIn(
            "Cannot register type " "<class 'test.fixtures.FooBar'> with qualifier 'foo' as it already exists.",
            str(context.exception),
        )

    def test_register_same_qualifier_should_raise(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="foo")

        with self.assertRaises(ValueError) as context:
            self.container.register(FooBaz, qualifier="foo")

        self.assertIn(
            "Cannot register implementation class "
            "<class 'test.fixtures.FooBaz'> for <class 'test.fixtures.FooBase'> "
            "with qualifier 'foo' as it already exists",
            str(context.exception),
        )

    def test_qualifier_raises_wire_called_on_unknown_type(self):
        @self.container.autowire
        def inner(sub1: FooBase = wire(qualifier="sub1")):
            ...

        self.container.abstract(FooBase)
        with self.assertRaises(ValueError) as context:
            inner()

        self.assertIn(
            "Cannot instantiate concrete class for <class 'test.fixtures.FooBase'> "
            "as qualifier 'sub1' is unknown. Available qualifiers: set()",
            str(context.exception),
        )

    def test_inject_abstract_directly_raises(self):
        @self.container.autowire
        def inner(sub1: FooBase):
            ...

        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="foobar")
        with self.assertRaises(Exception) as context:
            inner()

        self.assertIn(
            "Cannot instantiate abstract class <class 'inspect._empty'> directly. Available qualifiers {'foobar'}.",
            str(context.exception),
        )

    def test_register_with_qualifier_fails_when_invoked_without(self):
        @self.container.register(qualifier=__name__)
        class RegisterWithQualifierClass:
            ...

        @self.container.autowire
        def inner(foo: RegisterWithQualifierClass):
            ...

        with self.assertRaises(Exception) as context:
            inner()

        self.assertIn(
            f"Cannot instantiate concrete class for {RegisterWithQualifierClass} "
            "as qualifier 'None' is unknown. Available qualifiers: {'test_container'}",
            str(context.exception),
        )

    def test_register_with_qualifier_injects_based_on_qualifier(self):
        @self.container.register(qualifier=__name__)
        @dataclass
        class RegisterWithQualifierClass:
            foo = "bar"

        @self.container.autowire
        def inner(foo: RegisterWithQualifierClass = wire(qualifier=__name__)):
            self.assertEqual(foo.foo, "bar")

        inner()
        foo = self.container.get(RegisterWithQualifierClass, qualifier=__name__)
        self.assertEqual(foo.foo, "bar")

    def test_inject_qualifier_on_unknown_type(self):
        @self.container.autowire
        def inner(foo: str = wire(qualifier=__name__)):
            ...

        with self.assertRaises(ValueError) as context:
            inner()

        self.assertEqual(
            "Cannot use qualifier test_container on a type that is not managed by the container.",
            str(context.exception),
        )

    def test_register_supports_multiple_containers(self):
        c1 = DependencyContainer(ParameterBag())
        c2 = DependencyContainer(ParameterBag())

        c1.register(Counter)
        c2.register(Counter)

        c1.get(Counter).inc()
        self.assertEqual(c1.get(Counter).count, 1)
        self.assertEqual(c2.get(Counter).count, 0)
        c2.get(Counter).inc()
        self.assertEqual(c2.get(Counter).count, 1)

    def test_autowire_supports_multiple_containers(self):
        c1 = DependencyContainer(ParameterBag())
        c2 = DependencyContainer(ParameterBag())

        c1.params.put("param1", "param_value")
        c2.params.put("param1", "param_value")

        c1.register(Counter)
        c2.register(Counter)

        def inner(counter: Counter, p1: str = wire(param="param1")):
            counter.inc()
            self.assertEqual(counter.count, 1)
            self.assertEqual(p1, "param_value")

        c1.autowire(inner)()
        c2.autowire(inner)()
