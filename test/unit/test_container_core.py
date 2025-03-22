from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

import pytest
import wireup
from wireup import ParameterBag
from wireup.errors import UnknownServiceRequestedError, WireupError

from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.no_annotations.random.truly_random_service import TrulyRandomService
from test.unit.services.with_annotations.env import EnvService
from test.unit.services.with_annotations.services import Foo, FooImpl, ScopedService, TransientService
from test.unit.util import run

if TYPE_CHECKING:
    from test.conftest import Container


class ContainerGetParams(NamedTuple):
    service_type: type[Any]
    qualifier: str | None
    expected_type: type[Any]


@pytest.mark.parametrize(
    ContainerGetParams._fields,
    [
        pytest.param(
            *ContainerGetParams(service_type=EnvService, qualifier=None, expected_type=EnvService),
            id="Default qualifier",
        ),
        pytest.param(
            *ContainerGetParams(service_type=RandomService, qualifier="foo", expected_type=RandomService),
            id="With qualifier, from factory",
        ),
        pytest.param(*ContainerGetParams(service_type=Foo, qualifier=None, expected_type=FooImpl), id="With qualifier"),
    ],
)
async def test_container_get_with_qualifier_returns_service(
    container: Container, service_type: type[Any], qualifier: str, expected_type: type[Any]
) -> None:
    res = await run(container.get(service_type, qualifier=qualifier))

    assert isinstance(res, service_type)
    assert isinstance(res, expected_type)


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
