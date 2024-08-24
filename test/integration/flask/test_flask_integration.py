import unittest
from unittest.mock import MagicMock

import wireup
import wireup.integration
from flask import Flask
from typing_extensions import Annotated
from wireup import Inject
from wireup.integration import get_container
from wireup.integration.flask_integration import FlaskIntegration
from wireup.util import create_container

from test.fixtures import FooBase
from test.integration.flask import services
from test.integration.flask.services.foo import IsTestService
from test.unit.services.no_annotations.random.random_service import RandomService


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.get("/random")
    def _random(random: RandomService):
        return {"lucky_number": random.get_random()}

    @app.get("/env")
    def _env(is_debug: Annotated[bool, Inject(param="DEBUG")], is_test: Annotated[bool, Inject(param="TESTING")]):
        return {"debug": is_debug, "test": is_test}

    @app.get("/not-autowired")
    def _not_autowired():
        return "not autowired"

    @app.get("/intf")
    def _intf(foo: FooBase):
        return foo.foo

    @app.get("/foo")
    def _foo(foo: IsTestService):
        return {"test": foo.is_test}

    wireup.integration.setup(
        FlaskIntegration(
            create_container(service_modules=[services], parameters={"custom_params": True}),
            app,
            import_flask_config=True,
        ),
    )

    return app


class TestFlaskIntegration(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_get_random_is_autowired_only_from_type(self):
        res = self.client.get("/random")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, {"lucky_number": 4})

    def test_get_env_injects_from_params(self):
        res = self.client.get("/env")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, {"debug": False, "test": True})

    def test_will_not_autowire_when_no_injections_requested(self):
        res = self.client.get("/not-autowired")

        self.assertEqual(res.text, "not autowired")

    def test_autowires_view_with_interface(self):
        res = self.client.get("/intf")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "bar")

    def test_service_depends_on_flask_params(self):
        res = self.client.get("/foo")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, {"test": True})

    def test_service_override(self):
        mocked_foo = MagicMock()
        mocked_foo.is_test = "mocked"

        with get_container(self.app).override.service(IsTestService, new=mocked_foo):
            res = self.client.get("/foo")

            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json, {"test": "mocked"})
