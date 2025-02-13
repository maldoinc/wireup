import datetime
import functools
import unittest
from dataclasses import dataclass
from typing import Optional
from unittest.mock import Mock, patch

from typing_extensions import Annotated
from wireup import Inject, ServiceLifetime, Wire, register_all_in_module, wire
from wireup.errors import (
    DuplicateQualifierForInterfaceError,
    DuplicateServiceRegistrationError,
    InvalidRegistrationTypeError,
    UnknownQualifiedServiceRequestedError,
    UnknownServiceRequestedError,
    UsageOfQualifierOnUnknownObjectError,
)
from wireup.ioc.dependency_container import DependencyContainer
from wireup.ioc.parameter import ParameterBag, TemplatedString
from wireup.ioc.types import AnnotatedParameter, ParameterWrapper

from test.fixtures import Counter, FooBar, FooBase, FooBaz
from test.unit import services
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.no_annotations.random.truly_random_service import TrulyRandomService


class TestContainer(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.container = DependencyContainer(ParameterBag())
        register_all_in_module(self.container, services)

    def test_raises_on_unknown_dependency(self):
        class UnknownDep: ...

        self.assertRaises(UnknownServiceRequestedError, lambda: self.container.get(UnknownDep))

    def test_container_returns_singletons(self):
        self.container.register(Counter)
        c1 = self.container.get(Counter)
        c1.inc()

        self.assertEqual(c1.count, self.container.get(Counter).count)

    def test_works_simple_get_instance_with_other_service_injected(self):
        truly_random = self.container.get(TrulyRandomService)

        self.assertIsInstance(truly_random, TrulyRandomService)
        self.assertEqual(truly_random.get_truly_random(), 5)

    def test_get_class_with_param_bindings(self) -> None:
        @self.container.register
        class ServiceWithParams:
            def __init__(
                self,
                connection_str: str = Inject(param="connection_str"),
                cache_dir: str = Inject(expr="${cache_dir}/etc"),
            ) -> None:
                self.connection_str = connection_str
                self.cache_dir = cache_dir

        self.container.params.put("connection_str", "sqlite://memory")
        self.container.params.put("cache_dir", "/var/cache")
        svc = self.container.get(ServiceWithParams)

        self.assertEqual(svc.connection_str, "sqlite://memory")
        self.assertEqual(svc.cache_dir, "/var/cache/etc")

    @patch("importlib.import_module")
    def test_inject_fastapi_dep(self, mock_import_module):
        mock_import_module.return_value = Mock(Depends=Mock())
        result = Inject()
        self.assertEqual(result, mock_import_module.return_value.Depends.return_value)
        mock_import_module.assert_called_once_with("fastapi")

    def test_inject_using_annotated_empty_wire(self):
        @self.container.autowire
        def inner(random: Annotated[RandomService, Inject()]):
            self.assertEqual(random.get_random(), 4)

        inner()

    def test_inject_using_annotated_empty_wire_fails_to_inject_unknown(self):
        @self.container.autowire
        def inner(_random: Annotated[unittest.TestCase, Inject()]): ...

        with self.assertRaises(UnknownServiceRequestedError) as context:
            inner()

        self.assertEqual(
            f"Cannot wire unknown class {unittest.TestCase}. Use '@service' or '@abstract' to enable autowiring.",
            str(context.exception),
        )

    @patch("importlib.import_module")
    def test_injection_works_annotated(self, mock_import_module):
        mock_import_module.return_value = Mock(Depends=Mock())

        @self.container.autowire
        def inner(rand: Annotated[RandomService, Inject()]):
            self.assertEqual(rand.get_random(), 4)

        inner()

    def test_register_known_class(self):
        class TestRegisterKnown:
            pass

        self.container.register(TestRegisterKnown)
        with self.assertRaises(DuplicateServiceRegistrationError) as context:
            self.container.register(TestRegisterKnown)

        self.assertIn(
            f"Cannot register type {TestRegisterKnown} " "with qualifier 'None' as it already exists.",
            str(context.exception),
        )

    def test_autowire_sync(self):
        self.container.params.put("env", "test")

        def test_function(random: TrulyRandomService, env: str = Inject(param="env")) -> int:
            self.assertEqual(env, "test")
            return random.get_truly_random()

        autowired_fn = self.container.autowire(test_function)
        self.assertTrue(callable(autowired_fn))
        self.assertEqual(autowired_fn(), 5)

    async def test_autowire_async(self):
        self.container.params.put("env", "test")

        async def test_function(random: RandomService, env: str = Inject(param="env")) -> int:
            self.assertEqual(env, "test")
            return random.get_random()

        autowired_fn = self.container.autowire(test_function)
        self.assertTrue(callable(autowired_fn))
        self.assertEqual(await autowired_fn(), 4)

    def test_get_unknown_class(self):
        class TestGetUnknown:
            pass

        with self.assertRaises(UnknownServiceRequestedError) as context:
            self.container.get(TestGetUnknown)

        self.assertEqual(
            f"Cannot wire unknown class {TestGetUnknown}. Use '@service' or '@abstract' to enable autowiring.",
            str(context.exception),
        )

    def test_can_initialize_from_context_tests_add_update(self):
        @dataclass
        class NoHints:
            interpolated: str
            env: str
            mambo_number: int

        self.container.register(NoHints)

        self.container.context.add_dependency(
            NoHints,
            "interpolated",
            AnnotatedParameter(annotation=ParameterWrapper(TemplatedString("${first}-${second}"))),
        )
        self.container.context.add_dependency(
            NoHints, "mambo_number", AnnotatedParameter(annotation=ParameterWrapper("mambo_number"))
        )
        self.container.context.add_dependency(NoHints, "env", AnnotatedParameter(annotation=ParameterWrapper("env")))

        self.container.params.update({"first": "foo", "second": "bar", "env": "test", "mambo_number": 5})
        obj = self.container.get(NoHints)

        self.assertEqual(obj.interpolated, "foo-bar")
        self.assertEqual(obj.env, "test")
        self.assertEqual(obj.mambo_number, 5)

    def test_db_service_dataclass_with_params(self):
        @dataclass
        class MyDbService:
            connection_str: str = Inject(param="connection_str")
            cache_dir: str = Inject(expr="${cache_dir}/${auth.user}/db")

        self.container = DependencyContainer(ParameterBag())
        self.container.register(MyDbService)
        self.container.params.update(
            {"cache_dir": "/var/cache", "connection_str": "sqlite://memory", "auth.user": "anon"},
        )

        db = self.container.get(MyDbService)

        self.assertEqual(db.cache_dir, "/var/cache/anon/db")
        self.assertEqual(db.connection_str, "sqlite://memory")

    def test_locates_service_with_qualifier(self):
        self.container.register(Counter, qualifier=999)
        resolved = self.container.get(Counter, qualifier=999)
        self.assertEqual(resolved.count, 0)
        resolved.inc()
        self.assertEqual(resolved.count, 1)

    def test_raises_when_not_supplying_qualifier_registered_multiple(self):
        self.container.register(Counter, qualifier="foo_qualified")
        self.container.register(Counter, qualifier="foo_qualified2")

        with self.assertRaises(UnknownQualifiedServiceRequestedError) as context:
            self.container.get(Counter)

        self.assertEqual(
            f"Cannot create {Counter} as qualifier 'None' is unknown. "
            "Available qualifiers: ['foo_qualified', 'foo_qualified2'].",
            str(context.exception),
        )

    def test_raises_on_unknown_service(self):
        container = DependencyContainer(ParameterBag())
        with self.assertRaises(UnknownServiceRequestedError) as context:
            container.get(Counter)

        self.assertEqual(
            f"Cannot wire unknown class {Counter}. Use '@service' or '@abstract' to enable autowiring.",
            str(context.exception),
        )

    def test_two_qualifiers_are_injected(self):
        @self.container.autowire
        def inner(sub1: FooBase = Inject(qualifier="sub1"), sub2: FooBase = Inject(qualifier="sub2")):
            self.assertEqual(sub1.foo, "bar")
            self.assertEqual(sub2.foo, "baz")

        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="sub1")
        self.container.register(FooBaz, qualifier="sub2")
        inner()

    def test_default_impl_is_injected(self):
        @self.container.autowire
        def inner(sub1: FooBase, sub2: Annotated[FooBase, Inject(qualifier="baz")]):
            self.assertEqual(sub1.foo, "bar")
            self.assertEqual(sub2.foo, "baz")

        self.container.abstract(FooBase)
        self.container.register(FooBar)
        self.container.register(FooBaz, qualifier="baz")
        inner()

    def test_two_qualifiers_are_injected_annotated(self):
        @self.container.autowire
        def inner(
            sub1: Annotated[FooBase, Inject(qualifier="sub1")], sub2: Annotated[FooBase, Inject(qualifier="sub2")]
        ):
            self.assertEqual(sub1.foo, "bar")
            self.assertEqual(sub2.foo, "baz")

        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="sub1")
        self.container.register(FooBaz, qualifier="sub2")
        inner()

    def test_interface_with_single_implementation_no_qualifier_gets_autowired(self):
        @self.container.autowire
        def inner(foo: FooBase):
            self.assertEqual(foo.foo, "bar")

        self.container.abstract(FooBase)
        self.container.register(FooBar)
        inner()

    def test_get_with_interface_and_qualifier(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="sub1")

        foo = self.container.get(FooBase, qualifier="sub1")
        self.assertEqual(foo.foo, "bar")

    def test_register_twice_should_raise(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="foo")

        with self.assertRaises(DuplicateServiceRegistrationError) as context:
            self.container.register(FooBar, qualifier="foo")

        self.assertIn(
            f"Cannot register type {FooBar} with qualifier 'foo' as it already exists.",
            str(context.exception),
        )

    def test_register_same_qualifier_should_raise(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="foo")

        with self.assertRaises(DuplicateQualifierForInterfaceError) as context:
            self.container.register(FooBaz, qualifier="foo")

        self.assertIn(
            "Cannot register implementation class "
            "<class 'test.fixtures.FooBaz'> for <class 'test.fixtures.FooBase'> "
            "with qualifier 'foo' as it already exists",
            str(context.exception),
        )

    def test_qualifier_raises_wire_called_on_unknown_type(self):
        @self.container.autowire
        def inner(_sub1: FooBase = Inject(qualifier="sub1")): ...

        self.container.abstract(FooBase)
        with self.assertRaises(UnknownQualifiedServiceRequestedError) as context:
            inner()

        self.assertIn(
            "Cannot create <class 'test.fixtures.FooBase'> " "as qualifier 'sub1' is unknown. Available qualifiers: []",
            str(context.exception),
        )

    def test_inject_abstract_directly_raises(self):
        @self.container.autowire
        def inner(_sub1: FooBase): ...

        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="foobar")
        with self.assertRaises(Exception) as context:
            inner()

        self.assertEqual(
            f"Cannot create {FooBase} as qualifier 'None' is unknown. " "Available qualifiers: ['foobar'].",
            str(context.exception),
        )

    def test_inject_abstract_directly_with_no_impls_raises(self):
        @self.container.autowire
        def inner(_sub1: FooBase): ...

        self.container.abstract(FooBase)
        with self.assertRaises(Exception) as context:
            inner()

        self.assertEqual(
            f"Cannot create {FooBase} as qualifier 'None' is unknown. " "Available qualifiers: [].",
            str(context.exception),
        )

    def test_register_with_qualifier_fails_when_invoked_without(self):
        @self.container.register(qualifier=__name__)
        class RegisterWithQualifierClass: ...

        @self.container.autowire
        def inner(_foo: RegisterWithQualifierClass): ...

        with self.assertRaises(UnknownQualifiedServiceRequestedError) as context:
            inner()

        self.assertIn(
            f"Cannot create {RegisterWithQualifierClass} "
            f"as qualifier 'None' is unknown. Available qualifiers: ['{__name__}'].",
            str(context.exception),
        )

    def test_register_with_qualifier_injects_based_on_qualifier(self):
        @self.container.register(qualifier=__name__)
        @dataclass
        class RegisterWithQualifierClass:
            foo = "bar"

        @self.container.autowire
        def inner(foo: RegisterWithQualifierClass = Inject(qualifier=__name__)):
            self.assertEqual(foo.foo, "bar")

        inner()
        foo = self.container.get(RegisterWithQualifierClass, qualifier=__name__)
        self.assertEqual(foo.foo, "bar")

    def test_inject_qualifier_on_unknown_type(self):
        @self.container.autowire
        def inner(_foo: str = Inject(qualifier=__name__)): ...

        with self.assertRaises(UsageOfQualifierOnUnknownObjectError) as context:
            inner()

        self.assertEqual(
            f"Cannot use qualifier {__name__} on a type that is not managed by the container.",
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

        def inner(counter: Counter, p1: str = Inject(param="param1")):
            counter.inc()
            self.assertEqual(counter.count, 1)
            self.assertEqual(p1, "param_value")

        c1.autowire(inner)()
        c2.autowire(inner)()

    def test_container_get_with_interface_returns_impl(self):
        self.container.abstract(FooBase)
        self.container.register(FooBar)

        foo_bar = self.container.get(FooBase)
        self.assertEqual(foo_bar.foo, "bar")

    def test_wire_param_without_typing(self):
        @self.container.autowire
        def inner(name=Inject(param="name")):
            self.assertEqual(name, "foo")

        self.container.params.put("name", "foo")
        inner()

    def test_wire_from_annotation(self):
        @self.container.autowire
        def inner(
            name: Annotated[str, Inject(param="name")],
            env: Annotated[str, Inject(param="env")],
            env_name: Annotated[str, Inject(expr="${env}-${name}")],
        ):
            self.assertEqual(name, "foo")
            self.assertEqual(env, "test")
            self.assertEqual(env_name, "test-foo")

        self.container.params.put("name", "foo")
        self.container.params.put("env", "test")
        inner()

    def test_container_wires_none_values_from_parameter_bag(self):
        self.container.params.put("foo", None)

        @self.container.autowire
        def inner(name: Annotated[str, Inject(param="foo")], name2: str = Inject(param="foo")):
            self.assertIsNone(name)
            self.assertIsNone(name2)

        inner()

    def test_container_register_transient(self):
        self.container.register(Counter, lifetime=ServiceLifetime.TRANSIENT)
        c1 = self.container.get(Counter)
        c2 = self.container.get(Counter)

        c1.inc()
        self.assertEqual(c1.count, 1)
        self.assertEqual(c2.count, 0)

    def test_container_register_transient_nested(self):
        c = DependencyContainer(ParameterBag())

        c.register(TrulyRandomService, lifetime=ServiceLifetime.TRANSIENT)
        c.register(RandomService, lifetime=ServiceLifetime.TRANSIENT)
        c1 = c.get(TrulyRandomService)
        c2 = c.get(TrulyRandomService)

        self.assertNotEqual(c1, c2)
        self.assertNotEqual(c1.random_service, c2.random_service)

    def test_container_register_transient_nested_singletons(self):
        c = DependencyContainer(ParameterBag())

        c.register(TrulyRandomService, lifetime=ServiceLifetime.TRANSIENT)
        c.register(RandomService, lifetime=ServiceLifetime.SINGLETON)
        c1 = c.get(TrulyRandomService)
        c2 = c.get(TrulyRandomService)

        self.assertNotEqual(c1, c2)
        self.assertEqual(c1.random_service, c2.random_service)

    def test_injects_ctor(self):
        class Dummy:
            @self.container.autowire
            def __init__(self, rand_service: RandomService, env: str = Inject(param="env")):
                self.env = env
                self.rand_service = rand_service

            def do_thing(self):
                return f"Running in {self.env} with a result of {self.rand_service.get_random()}"

        self.container.params.put("env", "test")

        dummy = Dummy()
        self.assertEqual(dummy.do_thing(), "Running in test with a result of 4")

    def test_get_returns_same_container_proxy_not_instantiated(self):
        self.assertEqual(self.container.get(RandomService), self.container.get(RandomService))

    def test_get_returns_real_instance(self):
        first = self.container.get(RandomService)
        self.assertIsInstance(first, RandomService)

        self.assertEqual(4, first.get_random())

    def test_shrinks_context_on_autowire(self):
        class SomeClass:
            pass

        def provide_b(fn):
            @functools.wraps(fn)
            def __inner(*args, **kwargs):
                return fn(*args, **kwargs, b=SomeClass())

            return __inner

        @provide_b
        def target(a: RandomService, b: SomeClass, _c: Optional[datetime.datetime] = None):
            self.assertEqual(a.get_random(), 4)
            self.assertIsInstance(b, SomeClass)

        autowired = self.container.autowire(target)
        self.assertEqual(self.container.context.dependencies[target].keys(), {"a", "b"})
        # On the second call, container will drop b from dependencies as it is an unknown object.
        autowired()
        self.assertEqual(self.container.context.dependencies[target].keys(), {"a"})

    def test_raises_when_injecting_invalid_types(self):
        with self.assertRaises(InvalidRegistrationTypeError) as err:
            self.container.register(services)

        self.assertEqual(
            str(err.exception),
            f"Cannot register {services} with the container. " f"Allowed types are callables and types",
        )

    def test_returns_real_instances_on_second_build(self):
        class Foo:
            def bar(self):
                pass

        self.container.register(Foo, lifetime=ServiceLifetime.TRANSIENT)
        self.container.get(Foo).bar()

        self.assertIsInstance(self.container.get(Foo), Foo)

    async def test_container_overrides_already_passed_keyword_args(self):
        self.container.params.put("foo", "Foo")

        @self.container.autowire
        def sync_inner(name: Annotated[str, Inject(param="foo")]):
            self.assertEqual(name, "Foo")

        @self.container.autowire
        async def async_inner(name: Annotated[str, Inject(param="foo")]):
            self.assertEqual(name, "Foo")

        sync_inner(name="Ignored")
        await async_inner(name="Ignored")

    def test_inject_aliases(self) -> None:
        self.assertEqual(wire, Wire)

    def test_inject_alias_wire_same_behavior(self) -> None:
        container = DependencyContainer(ParameterBag())
        container.params.put("foo", "Foo")
        container.register(RandomService, qualifier="foo")

        @container.autowire
        def inner(
            foo: Annotated[str, Wire(param="foo")],
            foo_foo: Annotated[str, Wire(expr="${foo}-${foo}")],
            rand_service: Annotated[RandomService, Wire(qualifier="foo")],
        ):
            self.assertEqual(foo, "Foo")
            self.assertEqual(foo_foo, "Foo-Foo")
            self.assertEqual(rand_service.get_random(), 4)

        inner()

    def test_container_resolves_existing_instance_from_interface_service_locator(self) -> None:
        self.container.abstract(FooBase)
        self.container.register(FooBar)

        self.assertTrue(self.container.get(FooBase) is self.container.get(FooBase))

    def test_container_resolves_existing_instance_from_interface_autowire(self) -> None:
        self.container.abstract(FooBase)
        self.container.register(FooBar)

        @self.container.autowire
        def foo(x: FooBase) -> FooBase:
            return x

        self.assertTrue(foo() is foo())
        self.assertIsInstance(foo(), FooBar)

    def test_container_resolves_existing_instance_from_interface_with_qualifier(self) -> None:
        self.container.abstract(FooBase)
        self.container.register(FooBar, qualifier="bar")

        @self.container.autowire
        def foo(x: Annotated[FooBase, Inject(qualifier="bar")]) -> FooBase:
            return x

        self.assertTrue(foo() is foo())
        self.assertIsInstance(foo(), FooBar)


async def async_foo_factory() -> FooBar:
    return FooBar()


async def test_container_aget_returns_instance() -> None:
    container = DependencyContainer(ParameterBag())
    container.register(async_foo_factory, qualifier="foo")

    obj = await container.aget(FooBar, qualifier="foo")
    assert isinstance(obj, FooBar)
