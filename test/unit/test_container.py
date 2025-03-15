import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock, Mock, patch

import wireup
from typing_extensions import Annotated
from wireup import Inject
from wireup._decorators import inject_from_container
from wireup.annotation import Injected
from wireup.errors import (
    DuplicateQualifierForInterfaceError,
    DuplicateServiceRegistrationError,
    UnknownQualifiedServiceRequestedError,
    UnknownServiceRequestedError,
    UsageOfQualifierOnUnknownObjectError,
)
from wireup.ioc.parameter import TemplatedString
from wireup.ioc.types import AnnotatedParameter, ParameterWrapper

from test.fixtures import Counter, FooBar, FooBarChild, FooBarMultipleBases, FooBase, FooBaseAnother, FooBaz
from test.unit import services
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.no_annotations.random.truly_random_service import TrulyRandomService


class TestContainer(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.container = wireup.create_sync_container(service_modules=[services], parameters={"env_name": "test"})

    def test_raises_on_unknown_dependency(self):
        class UnknownDep: ...

        self.assertRaises(UnknownServiceRequestedError, lambda: self.container.get(UnknownDep))

    def test_container_returns_singletons(self):
        self.container._registry.register(Counter)
        c1 = self.container.get(Counter)
        c1.inc()

        self.assertEqual(c1.count, self.container.get(Counter).count)

    def test_works_simple_get_instance_with_other_service_injected(self):
        truly_random = self.container.get(TrulyRandomService, qualifier="foo")

        self.assertIsInstance(truly_random, TrulyRandomService)
        self.assertEqual(truly_random.get_truly_random(), 5)

    def test_get_class_with_param_bindings(self) -> None:
        class ServiceWithParams:
            def __init__(
                self,
                connection_str: Annotated[str, Inject(param="connection_str")],
                cache_dir: Annotated[str, Inject(expr="${cache_dir}/etc")],
            ) -> None:
                self.connection_str = connection_str
                self.cache_dir = cache_dir

        self.container._registry.register(ServiceWithParams)
        self.container.params.put("connection_str", "sqlite://memory")
        self.container.params.put("cache_dir", "/var/cache")
        svc = self.container.get(ServiceWithParams)

        self.assertEqual(svc.connection_str, "sqlite://memory")
        self.assertEqual(svc.cache_dir, "/var/cache/etc")

    @patch("importlib.import_module")
    def test_inject_fastapi_dep(self, mock_import_module: MagicMock):
        mock_import_module.return_value = Mock(Depends=Mock())
        result = Inject()
        self.assertEqual(result, mock_import_module.return_value.Depends.return_value)
        mock_import_module.assert_called_once_with("fastapi")

    def test_inject_using_annotated_empty_wire_fails_to_inject_unknown(self):
        @inject_from_container(self.container)
        def inner(_random: Annotated[unittest.TestCase, Inject()]): ...

        with self.assertRaises(UnknownServiceRequestedError) as context:
            inner()

        self.assertEqual(
            f"Cannot wire unknown class {unittest.TestCase}. Use '@service' or '@abstract' to enable autowiring.",
            str(context.exception),
        )

    def test_autowire_sync(self):
        self.container.params.put("env", "test")

        def test_function(
            random: Annotated[TrulyRandomService, Inject(qualifier="foo")], env: Annotated[str, Inject(param="env")]
        ) -> int:
            self.assertEqual(env, "test")
            return random.get_truly_random()

        autowired_fn = inject_from_container(self.container)(test_function)
        self.assertTrue(callable(autowired_fn))
        self.assertEqual(autowired_fn(), 5)

    async def test_autowire_async(self):
        container = wireup.create_async_container(parameters={"env_name": "test"}, service_modules=[services])

        async def test_function(
            random: Annotated[RandomService, Inject(qualifier="foo")], env: Annotated[str, Inject(param="env_name")]
        ) -> int:
            self.assertEqual(env, "test")
            return random.get_random()

        autowired_fn = inject_from_container(container)(test_function)
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

        self.container._registry.register(NoHints)

        self.container._registry.context.add_dependency(
            NoHints,
            "interpolated",
            AnnotatedParameter(klass=str, annotation=ParameterWrapper(TemplatedString("${first}-${second}"))),
        )
        self.container._registry.context.add_dependency(
            NoHints, "mambo_number", AnnotatedParameter(klass=str, annotation=ParameterWrapper("mambo_number"))
        )
        self.container._registry.context.add_dependency(
            NoHints, "env", AnnotatedParameter(klass=str, annotation=ParameterWrapper("env"))
        )

        self.container.params.update({"first": "foo", "second": "bar", "env": "test", "mambo_number": 5})
        obj = self.container.get(NoHints)

        self.assertEqual(obj.interpolated, "foo-bar")
        self.assertEqual(obj.env, "test")
        self.assertEqual(obj.mambo_number, 5)

    def test_db_service_dataclass_with_params(self):
        @dataclass
        class MyDbService:
            connection_str: Annotated[str, Inject(param="connection_str")]
            cache_dir: Annotated[str, Inject(expr="${cache_dir}/${auth.user}/db")]

        self.container = wireup.create_sync_container()
        self.container._registry.register(MyDbService)
        self.container.params.update(
            {"cache_dir": "/var/cache", "connection_str": "sqlite://memory", "auth.user": "anon"},
        )

        db = self.container.get(MyDbService)

        self.assertEqual(db.cache_dir, "/var/cache/anon/db")
        self.assertEqual(db.connection_str, "sqlite://memory")

    def test_locates_service_with_qualifier(self):
        self.container._registry.register(Counter, qualifier=999)
        resolved = self.container.get(Counter, qualifier=999)
        self.assertEqual(resolved.count, 0)
        resolved.inc()
        self.assertEqual(resolved.count, 1)

    def test_raises_when_not_supplying_qualifier_registered_multiple(self):
        self.container._registry.register(Counter, qualifier="foo_qualified")
        self.container._registry.register(Counter, qualifier="foo_qualified2")

        with self.assertRaises(UnknownQualifiedServiceRequestedError) as context:
            self.container.get(Counter)

        self.assertEqual(
            f"Cannot create {Counter} as qualifier 'None' is unknown. "
            "Available qualifiers: ['foo_qualified', 'foo_qualified2'].",
            str(context.exception),
        )

    def test_raises_on_unknown_service(self):
        container = wireup.create_sync_container()
        with self.assertRaises(UnknownServiceRequestedError) as context:
            container.get(Counter)

        self.assertEqual(
            f"Cannot wire unknown class {Counter}. Use '@service' or '@abstract' to enable autowiring.",
            str(context.exception),
        )

    def test_two_qualifiers_are_injected(self):
        @inject_from_container(self.container)
        def inner(
            sub1: Annotated[FooBase, Inject(qualifier="sub1")], sub2: Annotated[FooBase, Inject(qualifier="sub2")]
        ):
            self.assertEqual(sub1.foo, "bar")
            self.assertEqual(sub2.foo, "baz")

        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="sub1")
        self.container._registry.register(FooBaz, qualifier="sub2")
        inner()

    def test_default_impl_is_injected(self):
        @inject_from_container(self.container)
        def inner(sub1: Injected[FooBase], sub2: Annotated[FooBase, Inject(qualifier="baz")]):
            self.assertEqual(sub1.foo, "bar")
            self.assertEqual(sub2.foo, "baz")

        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar)
        self.container._registry.register(FooBaz, qualifier="baz")
        inner()

    def test_two_qualifiers_are_injected_annotated(self):
        @inject_from_container(self.container)
        def inner(
            sub1: Annotated[FooBase, Inject(qualifier="sub1")], sub2: Annotated[FooBase, Inject(qualifier="sub2")]
        ):
            self.assertEqual(sub1.foo, "bar")
            self.assertEqual(sub2.foo, "baz")

        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="sub1")
        self.container._registry.register(FooBaz, qualifier="sub2")
        inner()

    def test_interface_with_single_implementation_no_qualifier_gets_autowired(self):
        @inject_from_container(self.container)
        def inner(foo: Injected[FooBase]):
            self.assertEqual(foo.foo, "bar")

        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar)
        inner()

    def test_get_with_interface_and_qualifier(self):
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="sub1")

        foo = self.container.get(FooBase, qualifier="sub1")
        self.assertEqual(foo.foo, "bar")

    def test_register_twice_should_raise(self):
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="foo")

        with self.assertRaises(DuplicateServiceRegistrationError) as context:
            self.container._registry.register(FooBar, qualifier="foo")

        self.assertIn(
            f"Cannot register type {FooBar} with qualifier 'foo' as it already exists.",
            str(context.exception),
        )

    def test_register_same_qualifier_should_raise(self):
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="foo")

        with self.assertRaises(DuplicateQualifierForInterfaceError) as context:
            self.container._registry.register(FooBaz, qualifier="foo")

        self.assertIn(
            "Cannot register implementation class "
            "<class 'test.fixtures.FooBaz'> for <class 'test.fixtures.FooBase'> "
            "with qualifier 'foo' as it already exists",
            str(context.exception),
        )

    def test_qualifier_raises_wire_called_on_unknown_type(self):
        @inject_from_container(self.container)
        def inner(_sub1: Annotated[FooBase, Inject(qualifier="sub1")]): ...

        self.container._registry.register_abstract(FooBase)
        with self.assertRaises(UnknownQualifiedServiceRequestedError) as context:
            inner()

        self.assertIn(
            "Cannot create <class 'test.fixtures.FooBase'> as qualifier 'sub1' is unknown. Available qualifiers: []",
            str(context.exception),
        )

    def test_inject_abstract_directly_raises(self):
        @inject_from_container(self.container)
        def inner(_sub1: Injected[FooBase]): ...

        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="foobar")
        with self.assertRaises(Exception) as context:
            inner()

        self.assertEqual(
            f"Cannot create {FooBase} as qualifier 'None' is unknown. Available qualifiers: ['foobar'].",
            str(context.exception),
        )

    def test_inject_abstract_directly_with_no_impls_raises(self):
        @inject_from_container(self.container)
        def inner(_sub1: Injected[FooBase]): ...

        self.container._registry.register_abstract(FooBase)
        with self.assertRaises(Exception) as context:
            inner()

        self.assertEqual(
            f"Cannot create {FooBase} as qualifier 'None' is unknown. Available qualifiers: [].",
            str(context.exception),
        )

    def test_inherited_services_from_same_base_are_injected(self):
        @inject_from_container(self.container)
        def inner(
            parent: Annotated[FooBase, Inject(qualifier="parent")], child: Annotated[FooBase, Inject(qualifier="child")]
        ):
            self.assertEqual(parent.foo, "bar")
            self.assertEqual(child.foo, "bar_child")

        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="parent")
        self.container._registry.register(FooBarChild, qualifier="child")
        inner()

        parent = self.container.get(FooBase, qualifier="parent")
        self.assertEqual(parent.foo, "bar")

        child = self.container.get(FooBase, qualifier="child")
        self.assertEqual(child.foo, "bar_child")

    def test_services_from_multiple_bases_are_injected(self):
        @inject_from_container(self.container)
        def inner(sub: Injected[FooBase]):
            self.assertEqual(sub.foo, "bar_multiple_bases")

        @inject_from_container(self.container)
        def inner_another(sub: Injected[FooBaseAnother]):
            self.assertEqual(sub.foo, "bar_multiple_bases")

        self.container._registry.register_abstract(FooBase)
        self.container._registry.register_abstract(FooBaseAnother)
        self.container._registry.register(FooBarMultipleBases)
        inner()
        inner_another()

        foo = self.container.get(FooBase)
        self.assertEqual(foo.foo, "bar_multiple_bases")

        foo_another = self.container.get(FooBaseAnother)
        self.assertEqual(foo_another.foo, "bar_multiple_bases")

    def test_register_with_qualifier_fails_when_invoked_without(self):
        class RegisterWithQualifierClass: ...

        self.container._registry.register(RegisterWithQualifierClass, qualifier=__name__)

        @inject_from_container(self.container)
        def inner(_foo: Injected[RegisterWithQualifierClass]): ...

        with self.assertRaises(UnknownQualifiedServiceRequestedError) as context:
            inner()

        self.assertIn(
            f"Cannot create {RegisterWithQualifierClass} "
            f"as qualifier 'None' is unknown. Available qualifiers: ['{__name__}'].",
            str(context.exception),
        )

    def test_register_with_qualifier_injects_based_on_qualifier(self):
        @dataclass
        class RegisterWithQualifierClass:
            foo = "bar"

        self.container._registry.register(RegisterWithQualifierClass, qualifier=__name__)

        @inject_from_container(self.container)
        def inner(foo: Annotated[RegisterWithQualifierClass, Inject(qualifier=__name__)]):
            self.assertEqual(foo.foo, "bar")

        inner()
        foo = self.container.get(RegisterWithQualifierClass, qualifier=__name__)
        self.assertEqual(foo.foo, "bar")

    def test_inject_qualifier_on_unknown_type(self):
        @inject_from_container(self.container)
        def inner(_foo: Annotated[str, Inject(qualifier=__name__)]): ...

        with self.assertRaises(UsageOfQualifierOnUnknownObjectError) as context:
            inner()

        self.assertEqual(
            f"Cannot use qualifier {__name__} on a type that is not managed by the container.",
            str(context.exception),
        )

    def test_register_supports_multiple_containers(self):
        c1 = wireup.create_sync_container()
        c2 = wireup.create_sync_container()

        c1._registry.register(Counter)
        c2._registry.register(Counter)

        c1.get(Counter).inc()
        self.assertEqual(c1.get(Counter).count, 1)
        self.assertEqual(c2.get(Counter).count, 0)
        c2.get(Counter).inc()
        self.assertEqual(c2.get(Counter).count, 1)

    def test_autowire_supports_multiple_containers(self):
        c1 = wireup.create_sync_container()
        c2 = wireup.create_sync_container()

        c1.params.put("param1", "param_value")
        c2.params.put("param1", "param_value")

        c1._registry.register(Counter)
        c2._registry.register(Counter)

        def inner(counter: Annotated[Counter, Inject()], p1: Annotated[str, Inject(param="param1")]):
            counter.inc()
            self.assertEqual(counter.count, 1)
            self.assertEqual(p1, "param_value")

        inject_from_container(c1)(inner)()
        inject_from_container(c2)(inner)()

    def test_container_get_with_interface_returns_impl(self):
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar)

        foo_bar = self.container.get(FooBase)
        self.assertEqual(foo_bar.foo, "bar")

    def test_wire_from_annotation(self):
        @inject_from_container(self.container)
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

        @inject_from_container(self.container)
        def inner(name: Annotated[str, Inject(param="foo")], name2: Annotated[str, Inject(param="foo")]):
            self.assertIsNone(name)
            self.assertIsNone(name2)

        inner()

    def test_container_register_transient(self):
        self.container._registry.register(Counter, lifetime="transient")
        with self.container.enter_scope() as scoped:
            c1 = scoped.get(Counter)
            c2 = scoped.get(Counter)

            c1.inc()
            self.assertEqual(c1.count, 1)
            self.assertEqual(c2.count, 0)

    def test_container_register_transient_nested(self):
        with wireup.create_sync_container().enter_scope() as c:
            c._registry.register(TrulyRandomService, lifetime="transient")
            c._registry.register(RandomService, lifetime="transient")
            c1 = c.get(TrulyRandomService)
            c2 = c.get(TrulyRandomService)

            self.assertNotEqual(c1, c2)
            self.assertNotEqual(c1.random_service, c2.random_service)

    def test_container_register_transient_nested_singletons(self):
        with wireup.create_sync_container().enter_scope() as c:
            c._registry.register(TrulyRandomService, lifetime="transient")
            c._registry.register(RandomService, lifetime="singleton")
            c1 = c.get(TrulyRandomService)
            c2 = c.get(TrulyRandomService)

            self.assertNotEqual(c1, c2)
            self.assertEqual(c1.random_service, c2.random_service)

    def test_injects_ctor(self):
        class Dummy:
            @inject_from_container(self.container)
            def __init__(
                self,
                rand_service: Annotated[RandomService, Inject(qualifier="foo")],
                env: Annotated[str, Inject(param="env")],
            ):
                self.env = env
                self.rand_service = rand_service

            def do_thing(self):
                return f"Running in {self.env} with a result of {self.rand_service.get_random()}"

        self.container.params.put("env", "test")

        dummy = Dummy()
        self.assertEqual(dummy.do_thing(), "Running in test with a result of 4")

    async def test_container_overrides_already_passed_keyword_args(self):
        sync_container = wireup.create_sync_container(parameters={"foo": "Foo"})
        async_container = wireup.create_async_container(parameters={"foo": "Foo"})

        @inject_from_container(sync_container)
        def sync_inner(name: Annotated[str, Inject(param="foo")]):
            self.assertEqual(name, "Foo")

        @inject_from_container(async_container)
        async def async_inner(name: Annotated[str, Inject(param="foo")]):
            self.assertEqual(name, "Foo")

        sync_inner(name="Ignored")
        await async_inner(name="Ignored")

    def test_inject_alias_wire_same_behavior(self) -> None:
        container = wireup.create_sync_container()
        container.params.put("foo", "Foo")
        container._registry.register(RandomService, qualifier="foo")

        @inject_from_container(container)
        def inner(
            foo: Annotated[str, Inject(param="foo")],
            foo_foo: Annotated[str, Inject(expr="${foo}-${foo}")],
            rand_service: Annotated[RandomService, Inject(qualifier="foo")],
        ):
            self.assertEqual(foo, "Foo")
            self.assertEqual(foo_foo, "Foo-Foo")
            self.assertEqual(rand_service.get_random(), 4)

        inner()

    def test_container_resolves_existing_instance_from_interface_service_locator(self) -> None:
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar)

        self.assertTrue(self.container.get(FooBase) is self.container.get(FooBase))

    def test_container_resolves_existing_instance_from_interface_autowire(self) -> None:
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar)

        @inject_from_container(self.container)
        def foo(x: Injected[FooBase]) -> FooBase:
            return x

        self.assertTrue(foo() is foo())
        self.assertIsInstance(foo(), FooBar)

    def test_container_resolves_existing_instance_from_interface_with_qualifier(self) -> None:
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="bar")

        @inject_from_container(self.container)
        def foo(x: Annotated[FooBase, Inject(qualifier="bar")]) -> FooBase:
            return x

        self.assertTrue(foo() is foo())
        self.assertIsInstance(foo(), FooBar)


async def async_foo_factory() -> FooBar:
    return FooBar()


async def test_container_aget_returns_instance() -> None:
    container = wireup.create_async_container()
    container._registry.register(async_foo_factory, qualifier="foo")

    obj = await container.get(FooBar, qualifier="foo")
    assert isinstance(obj, FooBar)
