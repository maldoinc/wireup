import re
from dataclasses import dataclass

import pytest
import wireup
from typing_extensions import Annotated
from wireup._annotations import Inject, abstract, service
from wireup.errors import WireupError

from test.unit.services.no_annotations.random.random_service import RandomService


def test_dependencies_parameters_exist() -> None:
    @wireup.service
    def foo_service(_param: Annotated[str, wireup.Inject(param="foo")]) -> RandomService:
        return RandomService()

    with pytest.raises(
        WireupError,
        match=(
            "Parameter '_param' of Type test.unit.services.no_annotations.random.random_service.RandomService "
            "depends on an unknown Wireup parameter 'foo'."
        ),
    ):
        wireup.create_sync_container(services=[foo_service])


def test_parameters_exist_checks_expression() -> None:
    @wireup.service
    def foo_service(_param: Annotated[str, wireup.Inject(expr="${foo}-${foo}")]) -> RandomService:
        return RandomService()

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter '_param' of Type test.unit.services.no_annotations.random.random_service.RandomService "
            "depends on an unknown Wireup parameter 'foo' requested in expression '${foo}-${foo}'."
        ),
    ):
        wireup.create_sync_container(services=[foo_service])


def test_checks_dependencies_exist() -> None:
    class Foo: ...

    @wireup.service
    @dataclass
    class Bar:
        foo: Foo

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'foo' of Type test.unit.test_container_creation.Bar "
            "depends on an unknown service Type test.unit.test_container_creation.Foo with qualifier None."
        ),
    ):
        wireup.create_sync_container(services=[Bar])


def test_lifetimes_match() -> None:
    @wireup.service(lifetime="scoped")
    class ScopedService: ...

    @wireup.service
    @dataclass
    class SingletonService:
        scoped: ScopedService

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'scoped' of Type test.unit.test_container_creation.SingletonService depends on a service "
            "with a 'scoped' lifetime which is not supported. Singletons can only depend on other singletons."
        ),
    ):
        wireup.create_sync_container(services=[SingletonService, ScopedService])


def test_validates_dependencies_does_not_raise_correct_lifetime_via_interface() -> None:
    @wireup.abstract
    class Foo: ...

    @wireup.service
    class FooImpl(Foo): ...

    @dataclass
    @wireup.service
    class ServiceB:
        foo: Foo

    wireup.create_sync_container(services=[ServiceB, FooImpl, Foo])


def test_validates_dependencies_lifetimes_raises_when_using_interfaces() -> None:
    @wireup.abstract
    class Foo: ...

    @wireup.service(lifetime="scoped")
    class FooImpl(Foo): ...

    @dataclass
    @wireup.service
    class ServiceB:
        foo: Foo

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'foo' of Type test.unit.test_container_creation.ServiceB depends on a service "
            "with a 'scoped' lifetime which is not supported. Singletons can only depend on other singletons."
        ),
    ):
        wireup.create_sync_container(services=[ServiceB, FooImpl, Foo])


def test_validates_container_raises_when_cyclical_dependencies() -> None:
    class Foo:
        def __init__(self, bar): ...

    class Bar:
        def __init__(self, foo: Foo): ...

    @wireup.service
    def make_foo(bar: Bar) -> Foo:
        return Foo(bar)

    @wireup.service
    def make_bar(baz: Foo) -> Bar:
        return Bar(baz)

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Circular dependency detected for test.unit.test_container_creation.Bar "
            "(created via test.unit.test_container_creation.make_bar)"
            "\n -> test.unit.test_container_creation.Foo (created via test.unit.test_container_creation.make_foo)"
            "\n -> test.unit.test_container_creation.Bar (created via test.unit.test_container_creation.make_bar)"
        ),
    ):
        wireup.create_sync_container(services=[make_foo, make_bar])


def test_validates_container_does_not_raise_when_no_dependency_cycle() -> None:
    class Foo:
        def __init__(self, bar): ...

    class Bar:
        def __init__(self, foo: Foo): ...

    @wireup.service
    def make_foo(bar: Bar) -> Foo:
        return Foo(bar)

    @wireup.service
    def make_bar(baz: Annotated[Foo, Inject(qualifier="no_dependency")]) -> Bar:
        return Bar(baz)

    @wireup.service(qualifier="no_dependency")
    def make_foo_no_dependency() -> Foo:
        return Foo(None)

    wireup.create_sync_container(services=[make_foo, make_bar, make_foo_no_dependency])


def test_lifetimes_match_factories() -> None:
    class ScopedService: ...

    @wireup.service(lifetime="scoped")
    def _scoped_factory() -> ScopedService:
        return ScopedService()

    @dataclass
    class SingletonService:
        scoped: ScopedService

    @wireup.service
    def _singleton_factory(scoped: ScopedService) -> SingletonService:
        return SingletonService(scoped)

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'scoped' of Function test.unit.test_container_creation._singleton_factory depends on a service "
            "with a 'scoped' lifetime which is not supported. Singletons can only depend on other singletons."
        ),
    ):
        wireup.create_sync_container(services=[_scoped_factory, _singleton_factory])


def test_errors_not_decorated_service() -> None:
    class NotDecorated: ...

    with pytest.raises(
        WireupError,
        match=f"Service {NotDecorated} is not decorated with @abstract or @service",
    ):
        wireup.create_sync_container(services=[NotDecorated])


def test_registers_abstract() -> None:
    @abstract
    class Foo: ...

    @service
    class FooImpl(Foo): ...

    container = wireup.create_sync_container(services=[Foo, FooImpl])
    assert isinstance(container.get(Foo), FooImpl)
