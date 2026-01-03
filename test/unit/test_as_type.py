from typing import Protocol

import pytest
from wireup import create_sync_container, injectable
from wireup.errors import UnknownServiceRequestedError


def test_register_with_as_type():
    class FooProtocol(Protocol):
        def foo(self) -> str: ...

    @injectable(as_type=FooProtocol)
    class FooImpl:
        def foo(self) -> str:
            return "foo"

    container = create_sync_container(injectables=[FooImpl])

    # Should be resolvable via the abstraction
    instance = container.get(FooProtocol)
    assert isinstance(instance, FooImpl)
    assert instance.foo() == "foo"

    # Should NOT be resolvable via the implementation class directly
    with pytest.raises(UnknownServiceRequestedError):
        container.get(FooImpl)


def test_as_type_adapter_pattern():
    class BarProtocol(Protocol):
        def bar(self) -> str: ...

    @injectable
    class BarImpl:
        def bar(self) -> str:
            return "bar"

    @injectable
    def make_bar_protocol(impl: BarImpl) -> BarProtocol:
        return impl

    container = create_sync_container(injectables=[BarImpl, make_bar_protocol])

    # Implementation should be resolvable (standard registration)
    impl_instance = container.get(BarImpl)
    assert isinstance(impl_instance, BarImpl)
    assert impl_instance.bar() == "bar"

    # Abstraction should be resolvable via the adapter factory
    proto_instance = container.get(BarProtocol)
    assert isinstance(proto_instance, BarImpl)
    assert proto_instance.bar() == "bar"

    # Since BarImpl is singleton by default, and factory injects it, it should be the same instance
    assert proto_instance is impl_instance


def test_as_type_with_qualifier():
    class QualifierProto(Protocol):
        def q(self) -> str: ...

    @injectable(as_type=QualifierProto, qualifier="foo")
    class QualifierImpl:
        def q(self) -> str:
            return "q"

    container = create_sync_container(injectables=[QualifierImpl])

    # Should be resolvable with qualifier
    instance = container.get(QualifierProto, qualifier="foo")
    assert isinstance(instance, QualifierImpl)
    assert instance.q() == "q"

    # Should NOT be resolvable without qualifier (if only registered with one)
    with pytest.raises(UnknownServiceRequestedError):
        container.get(QualifierProto)

    # Should not be resolvable with wrong qualifier
    with pytest.raises(UnknownServiceRequestedError):
        container.get(QualifierProto, qualifier="bar")


def test_as_type_on_factory():
    class FactoryProto(Protocol):
        def f(self) -> str: ...

    class FactoryImpl:
        def f(self) -> str:
            return "f"

    @injectable(as_type=FactoryProto)
    def make_factory_impl() -> FactoryImpl:
        return FactoryImpl()

    container = create_sync_container(injectables=[make_factory_impl])

    # Should be resolvable via the abstraction
    instance = container.get(FactoryProto)
    assert isinstance(instance, FactoryImpl)
    assert instance.f() == "f"

    # Should NOT be resolvable via the implementation class directly
    with pytest.raises(UnknownServiceRequestedError):
        container.get(FactoryImpl)


def test_as_type_duck_typing():
    class DuckProto(Protocol):
        def quack(self) -> str: ...

    @injectable(as_type=DuckProto)
    class Duck:
        def quack(self) -> str:
            return "quack"

    container = create_sync_container(injectables=[Duck])

    instance = container.get(DuckProto)
    assert isinstance(instance, Duck)
    assert instance.quack() == "quack"
