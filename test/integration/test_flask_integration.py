import unittest
from test.services.random_service import RandomService

from flask import Flask
from typing_extensions import Annotated
from wireup import DependencyContainer, ParameterBag, Wire
from wireup.integration.flask_integration import wireup_init_flask_integration


class TestFlaskIntegration(unittest.TestCase):
    def setUp(self):
        self.container = DependencyContainer(ParameterBag())
        self.container.register(RandomService)

        self.app = Flask(__name__)
        self.app.config["TESTING"] = True

        self.client = self.app.test_client()

    def test_get_random_is_autowired_only_from_type(self):
        @self.app.get("/random")
        def get_random(random: RandomService):
            return {"lucky_number": random.get_random()}

        wireup_init_flask_integration(self.app, dependency_container=self.container, service_modules=[])
        res = self.client.get("/random")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, {"lucky_number": 4})

    def test_get_env_injects_from_params(self):
        @self.app.get("/env")
        def get_environment(
            is_debug: Annotated[bool, Wire(param="DEBUG")], is_test: Annotated[bool, Wire(param="TESTING")]
        ):
            return {"debug": is_debug, "test": is_test}

        wireup_init_flask_integration(self.app, dependency_container=self.container, service_modules=[])
        res = self.client.get("/env")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, {"debug": False, "test": True})

    def test_will_not_autowire_when_no_injections_requested(self):
        @self.app.get("/not-autowired")
        def will_not_get_autowired():
            return "not autowired"

        wireup_init_flask_integration(self.app, dependency_container=self.container, service_modules=[])
        res = self.client.get("/not-autowired")

        self.assertEqual(res.text, "not autowired")
        self.assertNotIn(will_not_get_autowired, self.container.context.dependencies)

    def test_registers_params_with_prefix(self):
        wireup_init_flask_integration(
            self.app, dependency_container=self.container, service_modules=[], config_prefix="flask"
        )

        self.assertEqual(False, self.container.params.get("flask.DEBUG"))
        self.assertEqual(True, self.container.params.get("flask.TESTING"))
