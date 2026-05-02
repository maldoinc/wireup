import re
import typing
from collections.abc import Hashable as AbcHashable
from collections.abc import Mapping as AbcMapping
from collections.abc import Sequence as AbcSequence
from dataclasses import dataclass
from typing import Annotated, Protocol

import pytest
import wireup
from wireup._annotations import Inject, abstract, injectable
from wireup.errors import WireupError

from test.unit.services.no_annotations.random.random_service import RandomService


def test_dependencies_parameters_exist() -> None:
    @wireup.injectable
    def foo_service(_param: Annotated[str, wireup.Inject(config="foo")]) -> RandomService:
        return RandomService()

    with pytest.raises(
        WireupError,
        match=re.escape(f"Parameter '_param' of {RandomService!r} depends on an unknown Wireup config key 'foo'."),
    ):
        wireup.create_sync_container(injectables=[foo_service])


def test_parameters_exist_checks_expression() -> None:
    @wireup.injectable
    def foo_service(_param: Annotated[str, wireup.Inject(expr="${foo}-${foo}")]) -> RandomService:
        return RandomService()

    with pytest.raises(
        WireupError,
        match=re.escape(
            f"Parameter '_param' of {RandomService!r} "
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
        match=re.escape(f"Parameter 'foo' of {Bar!r} has an unknown dependency on {Foo!r}."),
    ):
        wireup.create_sync_container(injectables=[Bar])


def test_checks_typing_sequence_dependency_uses_helpful_error() -> None:
    class Foo(Protocol): ...

    @wireup.injectable(as_type=Foo)
    class FooImpl:
        pass

    @wireup.injectable
    @dataclass
    class Bar:
        foo: typing.Sequence[Foo]

    with pytest.raises(
        WireupError,
        match=re.escape(
            f"Parameter 'foo' of {Bar!r} uses {typing.Sequence[Foo]!r}, "
            f"but Wireup collection injection requires {AbcSequence[Foo]!r}."
        ),
    ):
        wireup.create_sync_container(injectables=[FooImpl, Bar])


def test_checks_typing_mapping_dependency_uses_helpful_error() -> None:
    class Foo(Protocol): ...

    @wireup.injectable(as_type=Foo)
    class FooImpl:
        pass

    @wireup.injectable
    @dataclass
    class Bar:
        foo: typing.Mapping[str, Foo]

    with pytest.raises(
        WireupError,
        match=re.escape(
            f"Parameter 'foo' of {Bar!r} uses {typing.Mapping[str, Foo]!r}, "
            f"but Wireup collection injection requires {AbcMapping[AbcHashable, Foo]!r}."
        ),
    ):
        wireup.create_sync_container(injectables=[FooImpl, Bar])


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
            f"Parameter 'scoped' of {SingletonService!r} depends on an injectable "
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
            f"Parameter 'foo' of {ServiceB!r} depends on an injectable "
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
            f"Circular dependency detected for {Bar!r} "
            "with qualifier 'qualifier_name' "
            f"(created via {make_bar.__module__}.{make_bar.__name__})"
            f"\n -> {Foo!r} (created via {make_foo.__module__}.{make_foo.__name__})"
            f"\n -> {Bar!r} with qualifier 'qualifier_name' "
            f"(created via {make_bar.__module__}.{make_bar.__name__})"
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
            f"Parameter 'scoped' of {_singleton_factory!r} depends on an "
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
