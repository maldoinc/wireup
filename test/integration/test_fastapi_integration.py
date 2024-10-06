import unittest

import wireup
import wireup.integration
import wireup.integration.fastapi
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from typing_extensions import Annotated
from wireup import Inject
from wireup.errors import UnknownServiceRequestedError
from wireup.integration.fastapi import get_container

from test.unit.services.no_annotations.random.random_service import RandomService


def get_lucky_number() -> int:
    # Raise if this will be invoked more than once
    # That would be the case if wireup also "unwraps" and tries
    # to resolve dependencies it doesn't own.
    if hasattr(get_lucky_number, "_called"):
        raise Exception("Lucky Number was already invoked")

    get_lucky_number._called = True
    return 42


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/lucky-number")
    async def _(
        random_service: Annotated[RandomService, Inject()], lucky_number: Annotated[int, Depends(get_lucky_number)]
    ):
        return {"number": random_service.get_random(), "lucky_number": lucky_number}

    @app.get("/rng")
    async def _(random_service: Annotated[RandomService, Inject()]):
        return {"number": random_service.get_random()}

    @app.get("/params")
    async def _(foo: Annotated[str, Inject(param="foo")], foo_foo: Annotated[str, Inject(expr="${foo}-${foo}")]):
        return {"foo": foo, "foo_foo": foo_foo}

    @app.get("/raise-unknown")
    async def _(_unknown_service: Annotated[unittest.TestCase, Inject()]):
        return {"msg": "Hello World"}

    container = wireup.create_container(service_modules=[], parameters={"foo": "bar"})
    container.register(RandomService)
    wireup.integration.fastapi.setup(container, app)

    return app


class TestFastAPI(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_injects_service(self):
        response = self.client.get("/lucky-number")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"number": 4, "lucky_number": 42})

    def test_override(self):
        class RealRandom(RandomService):
            def get_random(self):
                return super().get_random() ** 2

        with get_container(self.app).override.service(RandomService, new=RealRandom()):
            response = self.client.get("/rng")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"number": 16})

    def test_injects_parameters(self):
        response = self.client.get("/params")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"foo": "bar", "foo_foo": "bar-bar"})

    def test_raises_on_unknown_service(self):
        with self.assertRaises(UnknownServiceRequestedError) as e:
            self.client.get("/raise-unknown")

        self.assertEqual(
            str(e.exception),
            f"Cannot wire unknown class {unittest.TestCase}. Use '@service' or '@abstract' to enable autowiring.",
        )
