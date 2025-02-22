import pytest
import wireup
from wireup.ioc.container.sync_container import SyncContainer

from test.unit import services


@pytest.fixture()
def sync_container() -> SyncContainer:
    return wireup.create_sync_container(service_modules=[services], parameters={"env_name": "test"})


@pytest.fixture()
def async_container() -> SyncContainer:
    return wireup.create_sync_container(service_modules=[services], parameters={"env_name": "test"})


@pytest.fixture(params=[wireup.create_sync_container, wireup.create_async_container])
def container(request: pytest.FixtureRequest) -> SyncContainer:
    return request.param(service_modules=[services], parameters={"env_name": "test"})
