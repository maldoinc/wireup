from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

import pytest
from wireup import create_sync_container, injectable
from wireup.errors import AsTypeMismatchError, InvalidAsTypeError, UnknownServiceRequestedError


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


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Union types not available in python versions")
def test_as_type_on_optional_factory_new_union_optional():
    container = create_sync_container(injectables=[make_optional_impl])

    # Should be resolvable via Optional[OptionalProto]
    # This requires the container to register it as Optional[OptionalProto] (or Proto | None)
    # because the factory returns Impl | None.

    instance = container.get(OptionalProto | None)
    assert isinstance(instance, OptionalImpl)
    assert instance.opt() == "opt"


class AbstractFoo(ABC):
    @abstractmethod
    def bar(self) -> str: ...


@injectable(as_type=AbstractFoo)
class AbstractFooImpl(AbstractFoo):
    def bar(self) -> str:
        return "bar"


def test_register_with_as_type_abc():
    container = create_sync_container(injectables=[AbstractFooImpl])

    # Should be resolvable via the abstraction
    instance = container.get(AbstractFoo)
    assert isinstance(instance, AbstractFooImpl)
    assert instance.bar() == "bar"

    # Should NOT be resolvable via the implementation class directly
    with pytest.raises(UnknownServiceRequestedError):
        container.get(AbstractFooImpl)


class FunctionProto(Protocol):
    def call(self) -> int: ...


class RealService:
    def call(self) -> int:
        return 42


def test_as_type_on_simple_function():
    @injectable(as_type=FunctionProto)
    def factory() -> RealService:
        return RealService()

    container = create_sync_container(injectables=[factory])

    svc = container.get(FunctionProto)
    assert svc.call() == 42
    assert isinstance(svc, RealService)


class DependencyProto(Protocol):
    def do_something(self) -> str: ...


class DependencyImpl:
    def do_something(self) -> str:
        return "dependency_impl"


@runtime_checkable
class RuntimeCacheProto(Protocol):
    def get(self, key: str) -> str | None: ...


@injectable(as_type=RuntimeCacheProto)
class RuntimeCacheImpl:
    def get(self, key: str) -> str | None:
        return key


class NonProtocolBaseForFactory:
    pass


class WrongImplForFactory:
    pass


class SomethingForInvalidAsTypeFactory:
    pass


@injectable
@dataclass
class ServiceWithDependency:
    dependency: DependencyProto


def test_as_type_factory_dependency_injection():
    # Test that a dependency produced by a factory with as_type
    # is correctly injected into another service.

    @injectable(as_type=DependencyProto)
    def make_dependency() -> DependencyImpl:
        return DependencyImpl()

    container = create_sync_container(injectables=[make_dependency, ServiceWithDependency])

    service = container.get(ServiceWithDependency)
    assert isinstance(service.dependency, DependencyImpl)
    assert service.dependency.do_something() == "dependency_impl"


def test_runtime_checkable_protocol_validation_passes():
    container = create_sync_container(injectables=[RuntimeCacheImpl])
    cache = container.get(RuntimeCacheProto)
    assert isinstance(cache, RuntimeCacheImpl)
    assert cache.get("x") == "x"


def test_as_type_rejects_incompatible_class_registration():
    class NonProtocolBase:
        pass

    @injectable(as_type=NonProtocolBase)
    class WrongImpl:
        pass

    with pytest.raises(
        AsTypeMismatchError,
        match="Cannot register implementation",
    ):
        create_sync_container(injectables=[WrongImpl])


def test_as_type_rejects_incompatible_factory_registration():
    @injectable(as_type=NonProtocolBaseForFactory)
    def make_wrong() -> WrongImplForFactory:
        return WrongImplForFactory()

    with pytest.raises(
        AsTypeMismatchError,
        match="Cannot register implementation",
    ):
        create_sync_container(injectables=[make_wrong])


def test_as_type_rejects_invalid_registration_key_for_class():
    @injectable(as_type=1)  # type: ignore[arg-type]
    class Something:
        pass

    with pytest.raises(
        InvalidAsTypeError,
        match="Invalid as_type value",
    ):
        create_sync_container(injectables=[Something])


def test_runtime_checkable_protocol_validation_fails():
    @runtime_checkable
    class RuntimeRequiredProto(Protocol):
        def required(self) -> int: ...

    @injectable(as_type=RuntimeRequiredProto)
    class WrongRuntimeImpl:
        pass

    with pytest.raises(
        AsTypeMismatchError,
        match="Cannot register implementation",
    ):
        create_sync_container(injectables=[WrongRuntimeImpl])


def test_as_type_rejects_invalid_registration_key_for_factory():
    @injectable(as_type=1)  # type: ignore[arg-type]
    def make_something() -> SomethingForInvalidAsTypeFactory:
        return SomethingForInvalidAsTypeFactory()

    with pytest.raises(
        InvalidAsTypeError,
        match="Invalid as_type value",
    ):
        create_sync_container(injectables=[make_something])
