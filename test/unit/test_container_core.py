from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

import pytest
from wireup import ParameterBag

from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.with_annotations.env import EnvService
from test.unit.util import run

if TYPE_CHECKING:
    from wireup.ioc.container.async_container import AsyncContainer
    from wireup.ioc.container.sync_container import SyncContainer


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
    container: SyncContainer | AsyncContainer, service: type[Any], qualifier: str
) -> None:
    res = await run(container.get(service, qualifier=qualifier))

    assert isinstance(res, service)


async def test_container_get_returns_service(container: SyncContainer | AsyncContainer) -> None:
    res = await run(container.get(EnvService))

    assert isinstance(res, EnvService)
    assert res.env_name == "test"


async def test_container_params_returns_bag(container: SyncContainer | AsyncContainer) -> None:
    assert isinstance(container.params, ParameterBag)
    assert container.params.get("env_name") == "test"
