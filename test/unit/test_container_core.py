from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple

import pytest
import wireup
from typing_extensions import Annotated
from wireup import ParameterBag
from wireup._annotations import Inject, service
from wireup.errors import DuplicateServiceRegistrationError, UnknownServiceRequestedError, WireupError

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
    ],
)
async def test_container_get(
    container: Container, service_type: type[Any], qualifier: str, expected_type: type[Any]
) -> None:
    res = await run(container.get(service_type, qualifier=qualifier))

    assert isinstance(res, service_type)
    assert isinstance(res, expected_type)


async def test_injects_parameters_dataclass():
    @service
    @dataclass
    class MyDbService:
        connection_str: Annotated[str, Inject(param="connection_str")]
        cache_dir: Annotated[str, Inject(expr="${cache_dir}/${auth.user}/db")]

    container = wireup.create_async_container(
        services=[MyDbService],
        parameters={
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


async def test_get_unknown_class(container: Container):
    class TestGetUnknown:
        pass

    with pytest.raises(
        UnknownServiceRequestedError,
        match=f"Cannot inject unknown service {TestGetUnknown}. Make sure it is registered with the container.",
    ):
        await run(container.get(TestGetUnknown))


async def test_container_get_interface_without_impls_raises(container: Container) -> None:
    with pytest.raises(
        WireupError,
        match=re.escape(
            f"Cannot create {InterfaceWithoutImpls} as qualifier 'None' is unknown. Available qualifiers: []."
        ),
    ):
        await run(container.get(InterfaceWithoutImpls))


async def test_container_get_returns_service(container: Container) -> None:
    res = await run(container.get(EnvService))

    assert isinstance(res, EnvService)
    assert res.env_name == "test"


async def test_container_params_returns_bag(container: Container) -> None:
    assert isinstance(container.params, ParameterBag)
    assert container.params.get("env_name") == "test"


async def test_container_raises_get_transient_scoped(container: Container) -> None:
    msg = (
        "Cannot create 'transient' or 'scoped' lifetime objects from the base container. "
        "Please enter a scope using container.enter_scope. "
        "If you are within a scope, use the scoped container instance to create dependencies."
    )

    with pytest.raises(WireupError, match=msg):
        await run(container.get(TransientService))

    with pytest.raises(WireupError, match=msg):
        await run(container.get(ScopedService))


def test_container_reuses_singleton_instance() -> None:
    container = wireup.create_sync_container(services=[Foo, FooImpl])

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
    @service
    class ServiceWithParams:
        def __init__(
            self,
            connection_str: Annotated[str, Inject(param="connection_str")],
            cache_dir: Annotated[str, Inject(expr="${cache_dir}/etc")],
        ) -> None:
            self.connection_str = connection_str
            self.cache_dir = cache_dir

    container = wireup.create_sync_container(
        services=[ServiceWithParams], parameters={"connection_str": "sqlite://memory", "cache_dir": "/var/cache"}
    )
    svc = container.get(ServiceWithParams)

    assert svc.connection_str == "sqlite://memory"
    assert svc.cache_dir == "/var/cache/etc"


def test_raises_multiple_definitions():
    @service
    class Multiple: ...

    with pytest.raises(
        DuplicateServiceRegistrationError,
        match=re.escape(f"Cannot register type {Multiple} with qualifier 'None' as it already exists."),
    ):
        wireup.create_sync_container(services=[Multiple, Multiple])
