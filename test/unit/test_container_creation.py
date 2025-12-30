import re
from dataclasses import dataclass

import pytest
import wireup
from typing_extensions import Annotated
from wireup._annotations import Inject, abstract, injectable
from wireup.errors import WireupError

from test.unit.services.no_annotations.random.random_service import RandomService


def test_dependencies_parameters_exist() -> None:
    @wireup.injectable
    def foo_service(_param: Annotated[str, wireup.Inject(config="foo")]) -> RandomService:
        return RandomService()

    with pytest.raises(
        WireupError,
        match=(
            "Parameter '_param' of Type test.unit.services.no_annotations.random.random_service.RandomService "
            "depends on an unknown Wireup config key 'foo'."
        ),
    ):
        wireup.create_sync_container(injectables=[foo_service])


def test_parameters_exist_checks_expression() -> None:
    @wireup.injectable
    def foo_service(_param: Annotated[str, wireup.Inject(expr="${foo}-${foo}")]) -> RandomService:
        return RandomService()

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter '_param' of Type test.unit.services.no_annotations.random.random_service.RandomService "
            "depends on an unknown Wireup config key 'foo' requested in expression '${foo}-${foo}'."
        ),
    ):
        wireup.create_sync_container(injectables=[foo_service])


def test_checks_dependencies_exist() -> None:
    class Foo: ...

    @wireup.injectable
    @dataclass
    class Bar:
        foo: Foo

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'foo' of Type test.unit.test_container_creation.Bar "
            "depends on an unknown injectable Type test.unit.test_container_creation.Foo with qualifier None."
        ),
    ):
        wireup.create_sync_container(injectables=[Bar])


def test_lifetimes_match() -> None:
    @wireup.injectable(lifetime="scoped")
    class ScopedService: ...

    @wireup.injectable
    @dataclass
    class SingletonService:
        scoped: ScopedService

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'scoped' of Type test.unit.test_container_creation.SingletonService depends on an injectable "
            "with a 'scoped' lifetime which is not supported. Singletons can only depend on other singletons."
        ),
    ):
        wireup.create_sync_container(injectables=[SingletonService, ScopedService])


def test_validates_dependencies_does_not_raise_correct_lifetime_via_interface() -> None:
    @wireup.abstract
    class Foo: ...

    @wireup.injectable
    class FooImpl(Foo): ...

    @dataclass
    @wireup.injectable
    class ServiceB:
        foo: Foo

    wireup.create_sync_container(injectables=[ServiceB, FooImpl, Foo])


def test_validates_dependencies_lifetimes_raises_when_using_interfaces() -> None:
    @wireup.abstract
    class Foo: ...

    @wireup.injectable(lifetime="scoped")
    class FooImpl(Foo): ...

    @dataclass
    @wireup.injectable
    class ServiceB:
        foo: Foo

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'foo' of Type test.unit.test_container_creation.ServiceB depends on an injectable "
            "with a 'scoped' lifetime which is not supported. Singletons can only depend on other singletons."
        ),
    ):
        wireup.create_sync_container(injectables=[ServiceB, FooImpl, Foo])


def test_validates_container_raises_when_cyclical_dependencies() -> None:
    class Foo:
        def __init__(self, bar): ...

    class Bar:
        def __init__(self, foo: Foo): ...

    @wireup.injectable
    def make_foo(bar: Annotated[Bar, Inject(qualifier="qualifier_name")]) -> Foo:
        return Foo(bar)

    @wireup.injectable(qualifier="qualifier_name")
    def make_bar(baz: Foo) -> Bar:
        return Bar(baz)

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Circular dependency detected for test.unit.test_container_creation.Bar "
            '(with qualifier "qualifier_name", created via test.unit.test_container_creation.make_bar)'
            "\n -> test.unit.test_container_creation.Foo (created via test.unit.test_container_creation.make_foo)"
            '\n -> test.unit.test_container_creation.Bar (with qualifier "qualifier_name", '
            "created via test.unit.test_container_creation.make_bar)"
            " ! Cycle here"
        ),
    ):
        wireup.create_sync_container(injectables=[make_foo, make_bar])


def test_validates_container_does_not_raise_when_no_dependency_cycle() -> None:
    class Foo:
        def __init__(self, bar): ...

    class Bar:
        def __init__(self, foo: Foo): ...

    @wireup.injectable
    def make_foo(bar: Bar) -> Foo:
        return Foo(bar)

    @wireup.injectable
    def make_bar(baz: Annotated[Foo, Inject(qualifier="no_dependency")]) -> Bar:
        return Bar(baz)

    @wireup.injectable(qualifier="no_dependency")
    def make_foo_no_dependency() -> Foo:
        return Foo(None)

    wireup.create_sync_container(injectables=[make_foo, make_bar, make_foo_no_dependency])


def test_lifetimes_match_factories() -> None:
    class ScopedService: ...

    @wireup.injectable(lifetime="scoped")
    def _scoped_factory() -> ScopedService:
        return ScopedService()

    @dataclass
    class SingletonService:
        scoped: ScopedService

    @wireup.injectable
    def _singleton_factory(scoped: ScopedService) -> SingletonService:
        return SingletonService(scoped)

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'scoped' of Function test.unit.test_container_creation._singleton_factory depends on an "
            "injectable with a 'scoped' lifetime which is not supported. Singletons can only depend "
            "on other singletons."
        ),
    ):
        wireup.create_sync_container(injectables=[_scoped_factory, _singleton_factory])


def test_errors_not_decorated_service() -> None:
    class NotDecorated: ...

    with pytest.raises(
        WireupError,
        match=f"Injectable {NotDecorated} is not decorated with @abstract or @injectable",
    ):
        wireup.create_sync_container(injectables=[NotDecorated])


def test_registers_abstract() -> None:
    @abstract
    class Foo: ...

    @injectable
    class FooImpl(Foo): ...

    container = wireup.create_sync_container(injectables=[Foo, FooImpl])
    assert isinstance(container.get(Foo), FooImpl)
