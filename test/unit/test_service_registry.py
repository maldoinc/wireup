from typing import NewType

import pytest
from wireup.errors import (
    DuplicateServiceRegistrationError,
    FactoryReturnTypeIsEmptyError,
    InvalidRegistrationTypeError,
)
from wireup.ioc.service_registry import ServiceRegistry

from test.unit.services.no_annotations.random.random_service import RandomService


@pytest.fixture
def registry():
    return ServiceRegistry()


def test_register_service(registry: ServiceRegistry) -> None:
    registry.register(MyService, qualifier="default", lifetime="singleton")

    assert MyService in registry.impls
    assert registry.is_impl_with_qualifier_known(MyService, "default")
    assert registry.is_type_with_qualifier_known(MyService, "default")
    assert registry.context.lifetime[MyService] == "singleton"

    with pytest.raises(DuplicateServiceRegistrationError):
        registry.register(MyService, qualifier="default", lifetime="singleton")


def test_register_abstract(registry: ServiceRegistry) -> None:
    registry.register_abstract(MyInterface)
    assert registry.is_interface_known(MyInterface)


def test_register_factory(registry: ServiceRegistry) -> None:
    registry.register(random_service_factory, lifetime="singleton")

    assert (RandomService, None) in registry.factories
    assert registry.impls[RandomService] == {None}

    def invalid_factory() -> None:
        pass

    with pytest.raises(FactoryReturnTypeIsEmptyError):
        registry.register(invalid_factory, lifetime="singleton")

    with pytest.raises(DuplicateServiceRegistrationError):
        registry.register(random_service_factory, lifetime="singleton")


def test_is_impl_known(registry: ServiceRegistry) -> None:
    assert MyService not in registry.impls

    registry.register(MyService, qualifier="default", lifetime="singleton")
    assert MyService in registry.impls


def test_is_impl_with_qualifier_known(registry: ServiceRegistry) -> None:
    assert not registry.is_impl_with_qualifier_known(MyService, "default")

    registry.register(MyService, qualifier="default", lifetime="singleton")
    assert registry.is_impl_with_qualifier_known(MyService, "default")


def test_is_type_with_qualifier_known(registry: ServiceRegistry) -> None:
    assert not registry.is_type_with_qualifier_known(MyService, "default")

    registry.register(MyService, qualifier="default", lifetime="singleton")
    assert registry.is_type_with_qualifier_known(MyService, "default")


def test_is_interface_known(registry: ServiceRegistry) -> None:
    assert not registry.is_interface_known(MyInterface)

    registry.register_abstract(MyInterface)
    assert registry.is_interface_known(MyInterface)


def test_registry_newtypes_class(registry: ServiceRegistry) -> None:
    class X:
        pass

    Y = NewType("Y", X)

    def y_factory() -> Y:
        return Y(X())

    registry.register(y_factory, lifetime="singleton")

    assert registry.context.lifetime[Y] == "singleton"


def test_registry_newtypes_anything(registry: ServiceRegistry) -> None:
    Y = NewType("Y", str)

    def y_factory() -> Y:
        return Y("Hi")

    registry.register(y_factory, lifetime="singleton")

    assert registry.context.lifetime[Y] == "singleton"


def test_register_invalid_target(registry: ServiceRegistry) -> None:
    with pytest.raises(InvalidRegistrationTypeError):
        registry.register(1)


class MyService:
    pass


class MyInterface:
    pass


def random_service_factory() -> RandomService:
    return RandomService()
