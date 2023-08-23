import unittest
import examples.services

from dataclasses import dataclass
from unittest.mock import Mock, patch

from wireup.ioc.container import Container, ContainerProxy
from wireup.ioc.container_util import ParameterWrapper
from wireup.ioc.parameter import ParameterBag, TemplatedString
from wireup.ioc.util import find_classes_in_module
from examples.services.random_service import RandomService
from examples.services.truly_random_service import TrulyRandomService


class TestContainer(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.container = Container(ParameterBag())
        self.container.register_all_in_module(examples.services)

    def test_works_simple_get_instance(self):
        rand = self.container.get(RandomService)

        assert isinstance(rand, ContainerProxy), "Assert that we never interact directly with the instantiated classes"
        assert rand.get_random() == 4, "Assert that proxy pass-through works"

    def test_raises_on_unknown_dependency(self):
        class UnknownDep:
            ...

        self.assertRaises(ValueError, lambda: self.container.get(UnknownDep))

    def test_container_returns_singletons(self):
        @dataclass
        class Counter:
            count: int = 0

            def inc(self):
                self.count += 1

        self.container.register(Counter)
        c1 = self.container.get(Counter)
        c1.inc()

        self.assertEqual(c1, self.container.get(Counter))
        self.assertEqual(c1.count, self.container.get(Counter).count)

    def test_works_simple_get_instance_with_other_service_injected(self):
        truly_random = self.container.get(TrulyRandomService)

        assert isinstance(truly_random, ContainerProxy)
        assert truly_random.get_truly_random() == 5

    def test_get_class_with_param_bindings(self) -> None:
        @self.container.register
        class ServiceWithParams:
            def __init__(
                self,
                connection_str: str = self.container.wire(param="connection_str"),
                cache_dir: str = self.container.wire(expr="${cache_dir}/etc"),
            ) -> None:
                self.connection_str = connection_str
                self.cache_dir = cache_dir

        self.container.params.put("connection_str", "sqlite://memory")
        self.container.params.put("cache_dir", "/var/cache")
        svc = self.container.get(ServiceWithParams)

        assert svc.connection_str == "sqlite://memory"
        assert svc.cache_dir == "/var/cache/etc"

    def test_inject_param(self):
        result = self.container.wire(param="value")
        self.assertIsInstance(result, ParameterWrapper)
        self.assertEqual(result.param, "value")

    def test_inject_expr(self):
        result = self.container.wire(expr="some ${param}")
        self.assertIsInstance(result, ParameterWrapper)
        self.assertIsInstance(result.param, TemplatedString)
        self.assertEqual(result.param.value, "some ${param}")

    def test_inject_dep(self):
        class TestInjectDep:
            foo: int = 4

        self.container.register(TestInjectDep)
        result = self.container.wire(dep=TestInjectDep)
        self.assertIsInstance(result, ContainerProxy)
        self.assertEqual(result.foo, 4)

    @patch("importlib.import_module")
    def test_inject_fastapi_dep(self, mock_import_module):
        mock_import_module.return_value = Mock(Depends=Mock())
        result = self.container.wire()
        self.assertEqual(result, mock_import_module.return_value.Depends.return_value)
        mock_import_module.assert_called_once_with("fastapi")

    @patch("importlib.import_module", side_effect=ModuleNotFoundError)
    def test_inject_missing_fastapi(self, _):
        with self.assertRaises(Exception) as context:
            self.container.wire()

        self.assertIn("One of param, expr, qualifier or dep must be set", str(context.exception))

    def test_get_known_class(self):
        class TestGetUnknown:
            pass

        self.container.register(TestGetUnknown)
        self.container.wire = Mock()
        result = self.container.get(TestGetUnknown)
        self.assertEqual(result, self.container.wire.return_value)
        self.container.wire.assert_called_once_with(dep=TestGetUnknown)

    def test_register_known_class(self):
        class TestRegisterKnown:
            pass

        self.container.register(TestRegisterKnown)
        with self.assertRaises(ValueError) as context:
            self.container.register(TestRegisterKnown)

        self.assertIn("Class already registered in container", str(context.exception))

    def test_autowire_sync(self):
        self.container.params.put("env", "test")

        def test_function(random: TrulyRandomService, env: str = self.container.wire(param="env")) -> int:
            self.assertEqual(env, "test")
            return random.get_truly_random()

        autowired_fn = self.container.autowire(test_function)
        self.assertTrue(callable(autowired_fn))
        self.assertEqual(autowired_fn(), 5)

    async def test_autowire_async(self):
        self.container.params.put("env", "test")

        async def test_function(random: RandomService, env: str = self.container.wire(param="env")) -> int:
            self.assertEqual(env, "test")
            return random.get_random()

        autowired_fn = self.container.autowire(test_function)
        self.assertTrue(callable(autowired_fn))
        self.assertEqual(await autowired_fn(), 4)

    def test_register_all_in_module(self):
        # These classes are registered in setup
        for c in find_classes_in_module(examples.services, glob_pattern):
            self.assertIsInstance(self.container.get(c), ContainerProxy)

    def test_get_unknown_class(self):
        class TestGetUnknown:
            pass

        with self.assertRaises(ValueError) as context:
            self.container.get(TestGetUnknown)

        self.assertIn(f"Cannot wire unknown class {TestGetUnknown}.", str(context.exception))

    def test_can_initialize_from_context(self):
        @dataclass
        class NoHints:
            interpolated: str
            env: str
            mambo_number: int

        self.container.initialization_context.add_param(NoHints, "interpolated", TemplatedString("${first}-${second}"))
        self.container.initialization_context.add_param(NoHints, "env", "env")
        self.container.initialization_context.add_param(NoHints, "mambo_number", "mambo_number")

        self.container.register(NoHints)
        self.container.params.update({"first": "foo", "second": "bar", "env": "test", "mambo_number": 5})
        obj = self.container.get(NoHints)

        self.assertEqual(obj.interpolated, "foo-bar")
        self.assertEqual(obj.env, "test")
        self.assertEqual(obj.mambo_number, 5)

    def test_db_service_dataclass_with_params(self):
        @dataclass
        class MyDbService:
            connection_str: str = self.container.wire(param="connection_str")
            cache_dir: str = self.container.wire(expr="${cache_dir}/${auth.user}/db")

        self.container = Container(ParameterBag())
        self.container.register(MyDbService)
        self.container.params.update(
            {"cache_dir": "/var/cache", "connection_str": "sqlite://memory", "auth.user": "anon"}
        )

        db = self.container.get(MyDbService)

        self.assertEqual(db.cache_dir, "/var/cache/anon/db")
        self.assertEqual(db.connection_str, "sqlite://memory")
