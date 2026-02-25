import sys
from typing import Any, NewType, Optional

import pytest
from typing_extensions import Annotated
from wireup import Inject, service
from wireup._annotations import AbstractDeclaration, InjectableDeclaration
from wireup.errors import (
    DuplicateServiceRegistrationError,
    FactoryReturnTypeIsEmptyError,
    InvalidRegistrationTypeError,
    WireupError,
)
from wireup.ioc.registry import ContainerRegistry

from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.with_annotations.services import Foo, FooImpl, FooImplWithInjected


def test_register_service() -> None:
    registry = ContainerRegistry(
        impls=[InjectableDeclaration(obj=MyService, qualifier="default", lifetime="singleton")]
    )

    assert MyService in registry.impls
    assert registry.is_impl_with_qualifier_known(MyService, "default")
    assert registry.is_type_with_qualifier_known(MyService, "default")
    assert registry.lifetime[MyService, "default"] == "singleton"

    with pytest.raises(DuplicateServiceRegistrationError):
        ContainerRegistry(
            impls=[
                InjectableDeclaration(obj=MyService, qualifier="default", lifetime="singleton"),
                InjectableDeclaration(obj=MyService, qualifier="default", lifetime="singleton"),
            ]
        )


def test_register_abstract() -> None:
    registry = ContainerRegistry(abstracts=[AbstractDeclaration(obj=MyInterface)])
    assert registry.is_interface_known(MyInterface)


def test_register_factory() -> None:
    registry = ContainerRegistry(impls=[InjectableDeclaration(obj=random_service_factory, lifetime="singleton")])

    assert RandomService in registry.factories
    assert registry.impls[RandomService] == {None}

    def invalid_factory() -> None:
        pass

    with pytest.raises(FactoryReturnTypeIsEmptyError):
        ContainerRegistry(impls=[InjectableDeclaration(obj=invalid_factory, lifetime="singleton")])

    with pytest.raises(DuplicateServiceRegistrationError):
        ContainerRegistry(
            impls=[
                InjectableDeclaration(obj=random_service_factory, lifetime="singleton"),
                InjectableDeclaration(obj=random_service_factory, lifetime="singleton"),
            ]
        )


def test_is_impl_known() -> None:
    registry = ContainerRegistry()
    assert MyService not in registry.impls

    registry = ContainerRegistry(
        impls=[InjectableDeclaration(obj=MyService, qualifier="default", lifetime="singleton")]
    )
    assert MyService in registry.impls


def test_is_impl_with_qualifier_known() -> None:
    registry = ContainerRegistry()
    assert not registry.is_impl_with_qualifier_known(MyService, "default")

    registry = ContainerRegistry(
        impls=[InjectableDeclaration(obj=MyService, qualifier="default", lifetime="singleton")]
    )
    assert registry.is_impl_with_qualifier_known(MyService, "default")


def test_is_type_with_qualifier_known() -> None:
    registry = ContainerRegistry()
    assert not registry.is_type_with_qualifier_known(MyService, "default")

    registry = ContainerRegistry(
        impls=[InjectableDeclaration(obj=MyService, qualifier="default", lifetime="singleton")]
    )
    assert registry.is_type_with_qualifier_known(MyService, "default")


def test_register_with_redundant_annotation() -> None:
    with pytest.warns(UserWarning, match=r"Redundant Injected\[T\] or Annotated\[T, Inject\(\)\] in parameter"):
        ContainerRegistry(
            abstracts=[AbstractDeclaration(obj=Foo)],
            impls=[
                InjectableDeclaration(obj=FooImpl),
                InjectableDeclaration(obj=FooImplWithInjected, lifetime="singleton"),
            ],
        )


def test_is_interface_known() -> None:
    registry = ContainerRegistry()
    assert not registry.is_interface_known(MyInterface)

    registry = ContainerRegistry(abstracts=[AbstractDeclaration(obj=MyInterface)])
    assert registry.is_interface_known(MyInterface)


def test_registry_newtypes_class() -> None:
    class X:
        pass

    Y = NewType("Y", X)

    def y_factory() -> Y:
        return Y(X())

    registry = ContainerRegistry(impls=[InjectableDeclaration(obj=y_factory, lifetime="singleton")])

    assert registry.lifetime[Y] == "singleton"


def test_registry_newtypes_anything() -> None:
    Y = NewType("Y", str)

    def y_factory() -> Y:
        return Y("Hi")

    registry = ContainerRegistry(impls=[InjectableDeclaration(obj=y_factory, lifetime="singleton")])

    assert registry.lifetime[Y] == "singleton"


def test_register_invalid_target() -> None:
    with pytest.raises(InvalidRegistrationTypeError):
        ContainerRegistry(impls=[InjectableDeclaration(obj=1)])


@pytest.mark.skipif(
    sys.version_info < (3, 10) or sys.version_info >= (3, 14),
    reason="Pydantic settings is only compatible with Python 3.10-3.13",
)
def test_register_factory_with_unknown_dependency_with_default() -> None:
    from pydantic_settings import BaseSettings  # noqa: PLC0415

    @service
    class Settings(BaseSettings): ...

    registry = ContainerRegistry(impls=[InjectableDeclaration(obj=Settings, lifetime="singleton")])
    assert Settings in registry.impls


def test_register_factory_with_unknown_dependency_no_default() -> None:
    class UnknownService: ...

    class MyLocalService: ...

    def factory_no_default(_: UnknownService) -> MyLocalService:
        return MyLocalService()

    with pytest.raises(WireupError, match="has an unknown dependency"):
        ContainerRegistry(impls=[InjectableDeclaration(obj=factory_no_default, lifetime="singleton")])


def test_register_service_with_untyped_defaults_and_varargs() -> None:
    class Thing:
        def __init__(
            self,
            x=1,
            some_config: Annotated[Optional[str], Inject(param="test_config")] = None,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            pass

    registry = ContainerRegistry(impls=[InjectableDeclaration(obj=Thing, lifetime="singleton")])
    assert Thing in registry.impls


class MyInterface:
    pass


def random_service_factory() -> RandomService:
    return RandomService()


class MyService:
    pass
