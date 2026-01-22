from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple, Optional

import pytest
import wireup
from typing_extensions import Annotated
from wireup._annotations import Inject, abstract, injectable
from wireup.errors import (
    DuplicateQualifierForInterfaceError,
    DuplicateServiceRegistrationError,
    UnknownServiceRequestedError,
    WireupError,
)
from wireup.ioc.configuration import ConfigStore

from test.unit import service_refs, services
from test.unit.services.abstract_multiple_bases import FooBase, FooBaseAnother
from test.unit.services.inheritance_test import ObjWithInheritance
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.no_annotations.random.truly_random_service import TrulyRandomService
from test.unit.services.with_annotations.env import EnvService
from test.unit.services.with_annotations.services import (
    Foo,
    FooImpl,
    InterfaceWithoutImpls,
    OtherFooImpl,
    ScopedService,
    TransientService,
)
from test.unit.util import run

if TYPE_CHECKING:
    from test.conftest import Container


class ContainerGetParams(NamedTuple):
    service_type: type[Any]
    qualifier: str | None
    expected_type: type[Any]

    def to_pytest(self, pytest_id: str) -> Any:
        return pytest.param(
            *ContainerGetParams(
                service_type=self.service_type, qualifier=self.qualifier, expected_type=self.expected_type
            ),
            id=pytest_id,
        )


@pytest.mark.parametrize(
    ContainerGetParams._fields,
    [
        ContainerGetParams(service_type=EnvService, qualifier=None, expected_type=EnvService).to_pytest(
            "Concrete type"
        ),
        ContainerGetParams(service_type=RandomService, qualifier="foo", expected_type=RandomService).to_pytest(
            "With qualifier, from factory"
        ),
        ContainerGetParams(service_type=Foo, qualifier=None, expected_type=FooImpl).to_pytest("With qualifier"),
        ContainerGetParams(service_type=Foo, qualifier="other", expected_type=OtherFooImpl).to_pytest(
            "Resolves interface"
        ),
        ContainerGetParams(service_type=ObjWithInheritance, qualifier=None, expected_type=ObjWithInheritance).to_pytest(
            "Resolves dependencies from base classes with stringified types"
        ),
    ],
)
async def test_container_get(
    container: Container, service_type: type[Any], qualifier: str, expected_type: type[Any]
) -> None:
    res = await run(container.get(service_type, qualifier=qualifier))

    assert isinstance(res, service_type)
    assert isinstance(res, expected_type)


async def test_injects_parameters_dataclass():
    @injectable
    @dataclass
    class MyDbService:
        connection_str: Annotated[str, Inject(config="connection_str")]
        connection_str_param: Annotated[str, Inject(param="connection_str")]
        cache_dir: Annotated[str, Inject(expr="${cache_dir}/${auth.user}/db")]

    container = wireup.create_async_container(
        injectables=[MyDbService],
        config={
            "env_name": "test",
            "cache_dir": "/var/cache",
            "connection_str": "sqlite://memory",
            "auth.user": "anon",
        },
    )
    db = await container.get(MyDbService)

    assert isinstance(db, MyDbService)
    assert db.cache_dir == "/var/cache/anon/db"
    assert db.connection_str == "sqlite://memory"
    assert db.connection_str_param == "sqlite://memory"


async def test_get_unknown_class(container: Container):
    class TestGetUnknown:
        pass

    with pytest.raises(
        UnknownServiceRequestedError,
        match=re.escape(
            f"Cannot create unknown injectable Type {TestGetUnknown.__module__}.{TestGetUnknown.__name__}. "
            "Make sure it is registered with the container."
        ),
    ):
        await run(container.get(TestGetUnknown))


async def test_container_get_interface_without_impls_raises(container: Container) -> None:
    with pytest.raises(
        WireupError,
        match=re.escape(
            "Cannot create unknown injectable Abcmeta "
            f"{InterfaceWithoutImpls.__module__}.{InterfaceWithoutImpls.__name__}. "
            "Make sure it is registered with the container."
        ),
    ):
        await run(container.get(InterfaceWithoutImpls))


async def test_container_get_interface_unknown_impl_errors_known_impls(container: Container) -> None:
    with pytest.raises(
        WireupError,
        match=re.escape(
            f"Cannot create unknown injectable Abcmeta {Foo.__module__}.{Foo.__name__} "
            "with qualifier 'does-not-exist'. Make sure it is registered with the container."
        ),
    ):
        await run(container.get(Foo, qualifier="does-not-exist"))


@pytest.mark.parametrize("first", [Foo, FooImpl])
@pytest.mark.parametrize("second", [FooImpl, Foo])
async def test_container_get_interface_returns_same_instance_as_get_type(
    container: Container,
    first: type[Foo],
    second: type[FooImpl],
) -> None:
    assert await run(container.get(first)) is await run(container.get(second))


async def test_container_get_interface_returns_same_instance(container: Container) -> None:
    assert await run(container.get(Foo)) is await run(container.get(Foo))


async def test_container_get_returns_service(container: Container) -> None:
    res = await run(container.get(EnvService))

    assert isinstance(res, EnvService)
    assert res.env_name == "test"


async def test_container_params_returns_bag(container: Container) -> None:
    assert isinstance(container.params, ConfigStore)
    assert container.params.get("env_name") == "test"


async def test_container_config_returns_store(container: Container) -> None:
    assert isinstance(container.config, ConfigStore)
    assert container.config.get("env_name") == "test"


async def test_container_raises_get_transient_scoped(container: Container) -> None:
    with pytest.raises(
        WireupError,
        match=re.escape(
            "Scope mismatch: Cannot resolve transient injectable "
            "Type test.unit.services.with_annotations.services.TransientService "
            "from the root container. Only Singleton injectables can be resolved without a scope. "
            "To resolve transient injectables, you must create a scope.\n"
            "See: https://maldoinc.github.io/wireup/latest/lifetimes_and_scopes/"
        ),
    ):
        await run(container.get(TransientService))

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Scope mismatch: Cannot resolve scoped injectable "
            "Type test.unit.services.with_annotations.services.ScopedService "
            "from the root container. Only Singleton injectables can be resolved without a scope. "
            "To resolve scoped injectables, you must create a scope.\n"
            "See: https://maldoinc.github.io/wireup/latest/lifetimes_and_scopes/"
        ),
    ):
        await run(container.get(ScopedService))


def test_container_reuses_singleton_instance() -> None:
    container = wireup.create_sync_container(injectables=[Foo, FooImpl])

    assert container.get(FooImpl) is container.get(FooImpl)


async def test_raises_on_unknown_dependency(container: Container):
    class UnknownDep: ...

    with pytest.raises(UnknownServiceRequestedError):
        await run(container.get(UnknownDep))


async def test_works_simple_get_instance_with_other_service_injected(container: Container):
    truly_random = await run(container.get(TrulyRandomService, qualifier="foo"))
    assert isinstance(truly_random, TrulyRandomService)
    assert truly_random.get_truly_random() == 5


def test_get_class_with_param_bindings() -> None:
    @injectable
    class ServiceWithParams:
        def __init__(
            self,
            connection_str: Annotated[str, Inject(config="connection_str")],
            cache_dir: Annotated[str, Inject(expr="${cache_dir}/etc")],
        ) -> None:
            self.connection_str = connection_str
            self.cache_dir = cache_dir

    container = wireup.create_sync_container(
        injectables=[ServiceWithParams], config={"connection_str": "sqlite://memory", "cache_dir": "/var/cache"}
    )
    svc = container.get(ServiceWithParams)

    assert svc.connection_str == "sqlite://memory"
    assert svc.cache_dir == "/var/cache/etc"


def test_raises_multiple_definitions():
    @injectable
    class Multiple: ...

    with pytest.raises(
        DuplicateServiceRegistrationError,
        match=re.escape(f"Cannot register type Type {Multiple.__module__}.{Multiple.__name__} as it already exists."),
    ):
        wireup.create_sync_container(injectables=[Multiple, Multiple])


def test_register_same_qualifier_should_raise():
    @abstract
    class F1Base: ...

    @injectable(qualifier="f1")
    class F1(F1Base): ...

    @injectable(qualifier="f1")
    class F11(F1Base): ...

    with pytest.raises(
        DuplicateQualifierForInterfaceError,
        match=re.escape(
            f"Cannot register implementation class Type {F11.__module__}.{F11.__name__} "
            f"with qualifier 'f1' for {F1Base} as it already exists",
        ),
    ):
        wireup.create_async_container(injectables=[F1Base, F1, F11])


async def test_injects_qualifiers():
    @abstract
    class FBase: ...

    @injectable
    class FDefault(FBase): ...

    @injectable(qualifier="f1")
    class F1(FBase): ...

    @injectable(qualifier="f2")
    class F2(FBase): ...

    container = wireup.create_async_container(injectables=[FBase, FDefault, F1, F2])
    assert isinstance(await container.get(FBase), FDefault)
    assert isinstance(await container.get(FBase, "f1"), F1)
    assert isinstance(await container.get(FBase, "f2"), F2)


def test_services_from_multiple_bases_are_injected():
    container = wireup.create_sync_container(
        injectables=[services], config={"env_name": "test", "env": "test", "name": "foo"}
    )

    foo = container.get(FooBase)
    assert foo.foo == "bar_multiple_bases"

    foo_another = container.get(FooBaseAnother)
    assert foo_another.foo == "bar_multiple_bases"


def test_inject_qualifier_on_unknown_type():
    with pytest.raises(
        UnknownServiceRequestedError,
        match=re.escape(
            f"Cannot create unknown injectable Type builtins.str with qualifier '{__name__}'. "
            "Make sure it is registered with the container."
        ),
    ):
        wireup.create_sync_container().get(str, qualifier=__name__)


def test_container_deduplicates_services_from_multiple_modules() -> None:
    # service_refs imports classes with @injectable from services.
    # This should not result in a duplicate error since the container should deduplicate classes
    # when imported from multiple modules.
    wireup.create_async_container(injectables=[services, service_refs], config={"env_name": "test"})


def test_container_properly_caches_none_result() -> None:
    counter = 0

    @wireup.injectable
    def make_none() -> RandomService | None:
        nonlocal counter
        counter += 1

        return None

    container = wireup.create_sync_container(injectables=[make_none])
    assert container.get(RandomService) is container.get(RandomService)
    assert counter == 1


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Union types not available in python versions")
def test_container_handles_optional_types_as_aliased() -> None:
    counter = 0

    @wireup.injectable
    def make_none() -> RandomService | None:
        nonlocal counter
        counter += 1

        return None

    container = wireup.create_sync_container(injectables=[make_none])
    assert container.get(RandomService | None) is container.get(Optional[RandomService])
    assert container.get(RandomService | None) is container.get(None | RandomService)
    assert container.get(RandomService) is container.get(Optional[RandomService])
    assert counter == 1


def test_container_config_compat() -> None:
    container = wireup.create_sync_container(injectables=[], parameters={"foo": "bar"})

    assert container.params.get("foo") == "bar"

    @wireup.inject_from_container(container)
    def main(foo: Annotated[str, Inject(param="foo")]) -> None:
        assert foo == "bar"

    main()


async def test_async_container_config_compat() -> None:
    container = wireup.create_async_container(injectables=[], parameters={"foo": "bar"})

    assert container.params.get("foo") == "bar"

    @wireup.inject_from_container(container)
    async def main(foo: Annotated[str, Inject(param="foo")]) -> None:
        assert foo == "bar"

    await main()


def test_container_registers_services_compat() -> None:
    @wireup.service
    class BackwardsCompatService: ...

    with pytest.warns(FutureWarning, match="Services have been renamed to Injectables"):
        container = wireup.create_sync_container(
            service_modules=[services],
            parameters={"env_name": "test"},
            services=[BackwardsCompatService],
        )

    assert isinstance(container.get(RandomService, qualifier="foo"), RandomService)
    assert isinstance(container.get(BackwardsCompatService), BackwardsCompatService)
