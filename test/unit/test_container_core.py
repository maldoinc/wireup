from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

import pytest
from wireup import ParameterBag
from wireup.errors import WireupError

from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.with_annotations.env import EnvService
from test.unit.services.with_annotations.services import ScopedService, TransientService
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


async def test_container_raises_get_transient_scoped(container: Container) -> None:
    msg = (
        "Cannot create 'transient' or 'scoped' lifetime objects from the base container. "
        "Please enter a scope using wireup.enter_scope or wireup.enter_async_scope. "
        "If you are within a scope, use the scoped container instance to create dependencies."
    )

    with pytest.raises(WireupError, match=msg):
        await run(container.get(TransientService))

    with pytest.raises(WireupError, match=msg):
        await run(container.get(ScopedService))
