import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock, Mock, patch

import wireup
from typing_extensions import Annotated
from wireup import Inject, Injected, inject_from_container
from wireup.errors import (
    DuplicateQualifierForInterfaceError,
    UnknownQualifiedServiceRequestedError,
    UnknownServiceRequestedError,
    UsageOfQualifierOnUnknownObjectError,
)

from test.fixtures import Counter, FooBar, FooBarChild, FooBarMultipleBases, FooBase, FooBaseAnother, FooBaz
from test.unit import services
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.no_annotations.random.truly_random_service import TrulyRandomService


class TestContainer(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.container = wireup.create_sync_container(
            service_modules=[services], parameters={"env_name": "test", "env": "test", "name": "foo"}
        )

    @patch("importlib.import_module")
    def test_inject_fastapi_dep(self, mock_import_module: MagicMock):
        mock_import_module.return_value = Mock(Depends=Mock())
        result = Inject()
        self.assertEqual(result, mock_import_module.return_value.Depends.return_value)
        mock_import_module.assert_called_once_with("fastapi")

    def test_inject_using_annotated_empty_wire_fails_to_inject_unknown(self):
        with self.assertRaises(UnknownServiceRequestedError) as context:
            self.container.get(unittest.TestCase)

        self.assertEqual(
            f"Cannot inject unknown service {unittest.TestCase}. Make sure it is registered with the container.",
            str(context.exception),
        )

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
            f"Cannot inject unknown service {Counter}. Make sure it is registered with the container.",
            str(context.exception),
        )

    def test_two_qualifiers_are_injected(self):
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="sub1")
        self.container._registry.register(FooBaz, qualifier="sub2")

        @inject_from_container(self.container)
        def inner(
            sub1: Annotated[FooBase, Inject(qualifier="sub1")], sub2: Annotated[FooBase, Inject(qualifier="sub2")]
        ):
            self.assertEqual(sub1.foo, "bar")
            self.assertEqual(sub2.foo, "baz")

        inner()

    def test_default_impl_is_injected(self):
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar)
        self.container._registry.register(FooBaz, qualifier="baz")

        @inject_from_container(self.container)
        def inner(sub1: Injected[FooBase], sub2: Annotated[FooBase, Inject(qualifier="baz")]):
            self.assertEqual(sub1.foo, "bar")
            self.assertEqual(sub2.foo, "baz")

        inner()

    def test_two_qualifiers_are_injected_annotated(self):
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="sub1")
        self.container._registry.register(FooBaz, qualifier="sub2")

        @inject_from_container(self.container)
        def inner(
            sub1: Annotated[FooBase, Inject(qualifier="sub1")], sub2: Annotated[FooBase, Inject(qualifier="sub2")]
        ):
            self.assertEqual(sub1.foo, "bar")
            self.assertEqual(sub2.foo, "baz")

        inner()

    def test_get_with_interface_and_qualifier(self):
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="sub1")

        foo = self.container.get(FooBase, qualifier="sub1")
        self.assertEqual(foo.foo, "bar")

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
        self.container._registry.register_abstract(FooBase)
        with self.assertRaises(UnknownQualifiedServiceRequestedError) as context:
            self.container.get(FooBase, qualifier="sub1")

        self.assertIn(
            "Cannot create <class 'test.fixtures.FooBase'> as qualifier 'sub1' is unknown. Available qualifiers: []",
            str(context.exception),
        )

    def test_inject_abstract_directly_raises(self):
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="foobar")

        with self.assertRaises(Exception) as context:
            self.container.get(FooBase)

        self.assertEqual(
            f"Cannot create {FooBase} as qualifier 'None' is unknown. Available qualifiers: ['foobar'].",
            str(context.exception),
        )

    def test_inject_abstract_directly_with_no_impls_raises(self):
        self.container._registry.register_abstract(FooBase)
        with self.assertRaises(Exception) as context:
            self.container.get(FooBase)

        self.assertEqual(
            f"Cannot create {FooBase} as qualifier 'None' is unknown. Available qualifiers: [].",
            str(context.exception),
        )

    def test_inherited_services_from_same_base_are_injected(self):
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register(FooBar, qualifier="parent")
        self.container._registry.register(FooBarChild, qualifier="child")

        @inject_from_container(self.container)
        def inner(
            parent: Annotated[FooBase, Inject(qualifier="parent")], child: Annotated[FooBase, Inject(qualifier="child")]
        ):
            self.assertEqual(parent.foo, "bar")
            self.assertEqual(child.foo, "bar_child")

        inner()

        parent = self.container.get(FooBase, qualifier="parent")
        self.assertEqual(parent.foo, "bar")

        child = self.container.get(FooBase, qualifier="child")
        self.assertEqual(child.foo, "bar_child")

    def test_services_from_multiple_bases_are_injected(self):
        self.container._registry.register_abstract(FooBase)
        self.container._registry.register_abstract(FooBaseAnother)
        self.container._registry.register(FooBarMultipleBases)

        @inject_from_container(self.container)
        def inner(sub: Injected[FooBase]):
            self.assertEqual(sub.foo, "bar_multiple_bases")

        @inject_from_container(self.container)
        def inner_another(sub: Injected[FooBaseAnother]):
            self.assertEqual(sub.foo, "bar_multiple_bases")

        inner()
        inner_another()

        foo = self.container.get(FooBase)
        self.assertEqual(foo.foo, "bar_multiple_bases")

        foo_another = self.container.get(FooBaseAnother)
        self.assertEqual(foo_another.foo, "bar_multiple_bases")

    def test_register_with_qualifier_fails_when_invoked_without(self):
        class RegisterWithQualifierClass: ...

        self.container._registry.register(RegisterWithQualifierClass, qualifier=__name__)

        with self.assertRaises(UnknownQualifiedServiceRequestedError) as context:
            self.container.get(RegisterWithQualifierClass)

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
        with self.assertRaises(UsageOfQualifierOnUnknownObjectError) as context:
            self.container.get(str, qualifier=__name__)

        self.assertEqual(
            f"Cannot use qualifier {__name__} on type {str} that is not managed by the container.",
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

        inner()

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
