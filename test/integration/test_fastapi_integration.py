import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing_extensions import Annotated

from test.services.no_annotations.random.random_service import RandomService
from wireup import Wire, ParameterBag, DependencyContainer
from wireup.errors import UnknownServiceRequestedError
from wireup.integration.fastapi_integration import wireup_init_fastapi_integration


class TestFastAPI(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.client = TestClient(self.app)
        self.container = DependencyContainer(ParameterBag())

    def test_injects_service(self):
        self.container.register(RandomService)

        @self.app.get("/")
        async def target(random_service: Annotated[RandomService, Wire()]):
            return {"number": random_service.get_random()}

        wireup_init_fastapi_integration(self.app, dependency_container=self.container, service_modules=[])
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"number": 4})

    def test_raises_on_unknown_service(self):
        @self.app.get("/")
        async def target(_unknown_service: Annotated[unittest.TestCase, Wire()]):
            return {"msg": "Hello World"}

        wireup_init_fastapi_integration(self.app, dependency_container=self.container, service_modules=[])

        with self.assertRaises(UnknownServiceRequestedError) as e:
            self.client.get("/")

        self.assertEqual(
            str(e.exception),
            f"Cannot wire unknown class {unittest.TestCase}. "
            "Use @Container.{register,abstract} to enable autowiring",
        )
