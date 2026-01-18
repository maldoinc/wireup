from typing import Union

import pytest
import wireup
from wireup.ioc.container.async_container import AsyncContainer
from wireup.ioc.container.sync_container import SyncContainer

from test.unit import services

Container = Union[SyncContainer, AsyncContainer]


@pytest.fixture(params=[wireup.create_sync_container, wireup.create_async_container])
def container(request: pytest.FixtureRequest) -> Container:
    return request.param(
        injectables=[services],
        config={"env_name": "test"},
    )
