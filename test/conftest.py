from typing import Union

import pytest
import wireup

from test.unit import services

Container = Union[wireup.SyncContainer, wireup.AsyncContainer]


@pytest.fixture(params=[wireup.create_sync_container, wireup.create_async_container])
def container(request: pytest.FixtureRequest) -> Container:
    return request.param(
        injectables=[services],
        config={"env_name": "test"},
    )
