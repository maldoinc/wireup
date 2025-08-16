from typing import Iterator

import pytest
import wireup
import wireup.integration.litestar
from litestar import Litestar, get
from litestar.testing import TestClient
from wireup._annotations import Injected
from wireup.integration.litestar import inject

from test.shared import shared_services
from test.shared.shared_services.greeter import GreeterService


@get("/")
@inject
async def index(greeter: Injected[GreeterService]) -> str:
    return greeter.greet("world")


@pytest.fixture
def app() -> Litestar:
    app = Litestar([index])
    container = wireup.create_async_container(
        service_modules=[shared_services, wireup.integration.litestar],
        parameters={"foo": "bar"},
    )
    wireup.integration.litestar.setup(container, app)
    return app


@pytest.fixture
def client(app: Litestar) -> Iterator[TestClient[Litestar]]:
    with TestClient(app) as test_client:
        yield test_client


def test_index(client: TestClient[Litestar]) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "Hello world"
