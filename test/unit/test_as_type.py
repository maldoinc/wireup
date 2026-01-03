from __future__ import annotations

from typing import Optional, Protocol

import pytest
from wireup import create_sync_container, injectable
from wireup.errors import UnknownServiceRequestedError


class FooProtocol(Protocol):
    def foo(self) -> str: ...


@injectable(as_type=FooProtocol)
class FooImpl:
    def foo(self) -> str:
        return "foo"


def test_register_with_as_type():
    container = create_sync_container(injectables=[FooImpl])

    # Should be resolvable via the abstraction
    instance = container.get(FooProtocol)
    assert isinstance(instance, FooImpl)
    assert instance.foo() == "foo"

    # Should NOT be resolvable via the implementation class directly
    with pytest.raises(UnknownServiceRequestedError):
        container.get(FooImpl)


class BarProtocol(Protocol):
    def bar(self) -> str: ...


@injectable
class BarImpl:
    def bar(self) -> str:
        return "bar"


@injectable
def make_bar_protocol(impl: BarImpl) -> BarProtocol:
    return impl


def test_as_type_adapter_pattern():
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


class QualifierProto(Protocol):
    def q(self) -> str: ...


@injectable(as_type=QualifierProto, qualifier="foo")
class QualifierImpl:
    def q(self) -> str:
        return "q"


def test_as_type_with_qualifier():
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


class FactoryProto(Protocol):
    def f(self) -> str: ...


class FactoryImpl:
    def f(self) -> str:
        return "f"


def test_as_type_on_factory():
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


class DuckProto(Protocol):
    def quack(self) -> str: ...


@injectable(as_type=DuckProto)
class Duck:
    def quack(self) -> str:
        return "quack"


def test_as_type_duck_typing():
    container = create_sync_container(injectables=[Duck])

    instance = container.get(DuckProto)
    assert isinstance(instance, Duck)
    assert instance.quack() == "quack"


class OptionalProto(Protocol):
    def opt(self) -> str: ...


class OptionalImpl:
    def opt(self) -> str:
        return "opt"


@injectable(as_type=OptionalProto)
def make_optional_impl() -> OptionalImpl | None:
    return OptionalImpl()


def test_as_type_on_optional_factory():
    container = create_sync_container(injectables=[make_optional_impl])

    # Should be resolvable via Optional[OptionalProto]
    # This requires the container to register it as Optional[OptionalProto] (or Proto | None)
    # because the factory returns Impl | None.

    instance = container.get(Optional[OptionalProto])
    assert isinstance(instance, OptionalImpl)
    assert instance.opt() == "opt"

    instance_union = container.get(OptionalProto | None)
    assert isinstance(instance_union, OptionalImpl)
    assert instance.opt() == "opt"
