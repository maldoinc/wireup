from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

import pytest
from wireup import ParameterBag

from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.with_annotations.env import EnvService
from test.unit.util import run

if TYPE_CHECKING:
    from test.conftest import Container


class ContainerGetParams(NamedTuple):
    service: type[Any]
    qualifier: str | None


@pytest.mark.parametrize(
    ContainerGetParams._fields,
    [
        pytest.param(*ContainerGetParams(service=EnvService, qualifier=None), id="Default qualifier"),
        pytest.param(*ContainerGetParams(service=RandomService, qualifier="foo"), id="With qualifier"),
    ],
)
async def test_container_get_with_qualifier_returns_service(
    container: Container, service: type[Any], qualifier: str
) -> None:
    res = await run(container.get(service, qualifier=qualifier))

    assert isinstance(res, service)


async def test_container_get_returns_service(container: Container) -> None:
    res = await run(container.get(EnvService))

    assert isinstance(res, EnvService)
    assert res.env_name == "test"


async def test_container_params_returns_bag(container: Container) -> None:
    assert isinstance(container.params, ParameterBag)
    assert container.params.get("env_name") == "test"
