import unittest

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from typing_extensions import Annotated
from wireup import DependencyContainer, Inject, ParameterBag
from wireup.errors import UnknownServiceRequestedError
from wireup.integration.fastapi_integration import wireup_init_fastapi_integration

from test.unit.services.no_annotations.random.random_service import RandomService


class TestFastAPI(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.client = TestClient(self.app)
        self.container = DependencyContainer(ParameterBag())

    def test_injects_service(self):
        self.container.register(RandomService)
        is_lucky_number_invoked = False

        def get_lucky_number() -> int:
            nonlocal is_lucky_number_invoked

            # Raise if this will be invoked more than once
            # That would be the case if wireup also "unwraps" and tries
            # to resolve dependencies it doesn't own.
            if is_lucky_number_invoked:
                raise Exception("Lucky Number was already invoked")

            is_lucky_number_invoked = True
            return 42

        @self.app.get("/")
        async def target(
            random_service: Annotated[RandomService, Inject()], lucky_number: Annotated[int, Depends(get_lucky_number)]
        ):
            return {"number": random_service.get_random(), "lucky_number": lucky_number}

        wireup_init_fastapi_integration(self.app, dependency_container=self.container, service_modules=[])
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"number": 4, "lucky_number": 42})

    def test_injects_parameters(self):
        self.container.params.put("foo", "bar")

        @self.app.get("/")
        async def target(
            foo: Annotated[str, Inject(param="foo")], foo_foo: Annotated[str, Inject(expr="${foo}-${foo}")]
        ):
            return {"foo": foo, "foo_foo": foo_foo}

        wireup_init_fastapi_integration(self.app, dependency_container=self.container, service_modules=[])
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"foo": "bar", "foo_foo": "bar-bar"})

    def test_raises_on_unknown_service(self):
        @self.app.get("/")
        async def target(_unknown_service: Annotated[unittest.TestCase, Inject()]):
            return {"msg": "Hello World"}

        wireup_init_fastapi_integration(self.app, dependency_container=self.container, service_modules=[])
        with self.assertRaises(UnknownServiceRequestedError) as e:
            self.client.get("/")

        self.assertEqual(
            str(e.exception),
            f"Cannot wire unknown class {unittest.TestCase}. "
            "Use @Container.{register,abstract} to enable autowiring",
        )
