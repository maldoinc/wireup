from typing import NewType

import pytest
from wireup._annotations import AbstractDeclaration, ServiceDeclaration
from wireup.errors import (
    DuplicateServiceRegistrationError,
    FactoryReturnTypeIsEmptyError,
    InvalidRegistrationTypeError,
)
from wireup.ioc.service_registry import ServiceRegistry

from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.with_annotations.services import Foo, FooImplWithInjected


def test_register_service() -> None:
    registry = ServiceRegistry(impls=[ServiceDeclaration(obj=MyService, qualifier="default", lifetime="singleton")])

    assert MyService in registry.impls
    assert registry.is_impl_with_qualifier_known(MyService, "default")
    assert registry.is_type_with_qualifier_known(MyService, "default")
    assert registry.lifetime[MyService] == "singleton"

    with pytest.raises(DuplicateServiceRegistrationError):
        ServiceRegistry(
            impls=[
                ServiceDeclaration(obj=MyService, qualifier="default", lifetime="singleton"),
                ServiceDeclaration(obj=MyService, qualifier="default", lifetime="singleton"),
            ]
        )


def test_register_abstract() -> None:
    registry = ServiceRegistry(abstracts=[AbstractDeclaration(obj=MyInterface)])
    assert registry.is_interface_known(MyInterface)


def test_register_factory() -> None:
    registry = ServiceRegistry(impls=[ServiceDeclaration(obj=random_service_factory, lifetime="singleton")])

    assert (RandomService, None) in registry.factories
    assert registry.impls[RandomService] == {None}

    def invalid_factory() -> None:
        pass

    with pytest.raises(FactoryReturnTypeIsEmptyError):
        ServiceRegistry(impls=[ServiceDeclaration(obj=invalid_factory, lifetime="singleton")])

    with pytest.raises(DuplicateServiceRegistrationError):
        ServiceRegistry(
            impls=[
                ServiceDeclaration(obj=random_service_factory, lifetime="singleton"),
                ServiceDeclaration(obj=random_service_factory, lifetime="singleton"),
            ]
        )


def test_is_impl_known() -> None:
    registry = ServiceRegistry()
    assert MyService not in registry.impls

    registry = ServiceRegistry(impls=[ServiceDeclaration(obj=MyService, qualifier="default", lifetime="singleton")])
    assert MyService in registry.impls


def test_is_impl_with_qualifier_known() -> None:
    registry = ServiceRegistry()
    assert not registry.is_impl_with_qualifier_known(MyService, "default")

    registry = ServiceRegistry(impls=[ServiceDeclaration(obj=MyService, qualifier="default", lifetime="singleton")])
    assert registry.is_impl_with_qualifier_known(MyService, "default")


def test_is_type_with_qualifier_known() -> None:
    registry = ServiceRegistry()
    assert not registry.is_type_with_qualifier_known(MyService, "default")

    registry = ServiceRegistry(impls=[ServiceDeclaration(obj=MyService, qualifier="default", lifetime="singleton")])
    assert registry.is_type_with_qualifier_known(MyService, "default")


def test_register_with_redundant_annotation() -> None:
    with pytest.warns(UserWarning, match=r"Redundant Injected\[T\] or Annotated\[T, Inject\(\)\] in parameter"):
        ServiceRegistry(
            impls=[ServiceDeclaration(obj=Foo), ServiceDeclaration(obj=FooImplWithInjected, lifetime="singleton")],
        )


def test_is_interface_known() -> None:
    registry = ServiceRegistry()
    assert not registry.is_interface_known(MyInterface)

    registry = ServiceRegistry(abstracts=[AbstractDeclaration(obj=MyInterface)])
    assert registry.is_interface_known(MyInterface)


def test_registry_newtypes_class() -> None:
    class X:
        pass

    Y = NewType("Y", X)

    def y_factory() -> Y:
        return Y(X())

    registry = ServiceRegistry(impls=[ServiceDeclaration(obj=y_factory, lifetime="singleton")])

    assert registry.lifetime[Y] == "singleton"


def test_registry_newtypes_anything() -> None:
    Y = NewType("Y", str)

    def y_factory() -> Y:
        return Y("Hi")

    registry = ServiceRegistry(impls=[ServiceDeclaration(obj=y_factory, lifetime="singleton")])

    assert registry.lifetime[Y] == "singleton"


def test_register_invalid_target() -> None:
    with pytest.raises(InvalidRegistrationTypeError):
        ServiceRegistry(impls=[ServiceDeclaration(obj=1)])


class MyService:
    pass


class MyInterface:
    pass


def random_service_factory() -> RandomService:
    return RandomService()
