import unittest
from dataclasses import dataclass
from unittest.mock import Mock, patch

import examples.services
from examples.services.random_service import RandomService
from examples.services.truly_random_service import TrulyRandomService
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

        assert c1.count == self.container.get(Counter).count

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
        assert isinstance(result, ParameterWrapper)
        assert result.param == "value"

    def test_inject_expr(self):
        result = self.container.wire(expr="some ${param}")
        assert isinstance(result, ParameterWrapper)
        assert isinstance(result.param, TemplatedString)
        assert result.param.value == "some ${param}"

    def test_inject_dep(self):
        class TestInjectDep:
            foo: int = 4

        self.container.register(TestInjectDep)
        result = self.container.wire(dep=TestInjectDep)
        assert isinstance(result, ContainerProxy)
        assert result.foo == 4

    @patch("importlib.import_module")
    def test_inject_fastapi_dep(self, mock_import_module):
        mock_import_module.return_value = Mock(Depends=Mock())
        result = self.container.wire()
        assert result == mock_import_module.return_value.Depends.return_value
        mock_import_module.assert_called_once_with("fastapi")

    @patch("importlib.import_module", side_effect=ModuleNotFoundError)
    def test_inject_missing_fastapi(self, _):
        with self.assertRaises(Exception) as context:
            self.container.wire()

        assert "One of param, expr, qualifier or dep must be set" in str(context.exception)

    def test_get_known_class(self):
        class TestGetUnknown:
            pass

        self.container.register(TestGetUnknown)
        self.container.wire = Mock()
        result = self.container.get(TestGetUnknown)
        assert result == self.container.wire.return_value
        self.container.wire.assert_called_once_with(dep=TestGetUnknown)

    def test_register_known_class(self):
        class TestRegisterKnown:
            pass

        self.container.register(TestRegisterKnown)
        with self.assertRaises(ValueError) as context:
            self.container.register(TestRegisterKnown)

        assert "Class already registered in container" in str(context.exception)

    def test_autowire_sync(self):
        self.container.params.put("env", "test")

        def test_function(random: TrulyRandomService, env: str = self.container.wire(param="env")) -> int:
            assert env == "test"
            return random.get_truly_random()

        autowired_fn = self.container.autowire(test_function)
        assert callable(autowired_fn)
        assert autowired_fn() == 5

    async def test_autowire_async(self):
        self.container.params.put("env", "test")

        async def test_function(random: RandomService, env: str = self.container.wire(param="env")) -> int:
            assert env == "test"
            return random.get_random()

        autowired_fn = self.container.autowire(test_function)
        assert callable(autowired_fn)
        assert await autowired_fn() == 4

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

        assert obj.interpolated == "foo-bar"
        assert obj.env == "test"
        assert obj.mambo_number == 5

    def test_db_service_dataclass_with_params(self):
        @dataclass
        class MyDbService:
            connection_str: str = self.container.wire(param="connection_str")
            cache_dir: str = self.container.wire(expr="${cache_dir}/${auth.user}/db")

        self.container = DependencyContainer(ParameterBag())
        self.container.register(MyDbService)
        self.container.params.update(
            {"cache_dir": "/var/cache", "connection_str": "sqlite://memory", "auth.user": "anon"},
        )

        db = self.container.get(MyDbService)

        assert db.cache_dir == "/var/cache/anon/db"
        assert db.connection_str == "sqlite://memory"
