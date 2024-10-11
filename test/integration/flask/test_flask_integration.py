from unittest.mock import MagicMock

import pytest
import wireup.integration.flask
from flask import Flask
from flask.testing import FlaskClient
from typing_extensions import Annotated
from wireup import Inject, create_container
from wireup.integration.flask import get_container

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

    wireup.integration.flask.setup(
        create_container(service_modules=[services], parameters={"custom_params": True}), app, import_flask_config=True
    )

    return app


@pytest.fixture
def app() -> Flask:
    return create_app()


@pytest.fixture
def client(app: Flask):
    return app.test_client()


def test_get_random_is_autowired_only_from_type(client: FlaskClient) -> None:
    res = client.get("/random")
    assert res.status_code == 200
    assert res.json == {"lucky_number": 4}


def test_get_env_injects_from_params(client: FlaskClient) -> None:
    res = client.get("/env")
    assert res.status_code == 200
    assert res.json == {"debug": False, "test": True}


def test_will_not_autowire_when_no_injections_requested(client: FlaskClient) -> None:
    res = client.get("/not-autowired")
    assert res.data.decode() == "not autowired"


def test_autowires_view_with_interface(client: FlaskClient) -> None:
    res = client.get("/intf")
    assert res.status_code == 200
    assert res.data.decode() == "bar"


def test_service_depends_on_flask_params(client: FlaskClient) -> None:
    res = client.get("/foo")
    assert res.status_code == 200
    assert res.json == {"test": True}


def test_service_override(client: FlaskClient, app: Flask):
    mocked_foo = MagicMock()
    mocked_foo.is_test = "mocked"

    with get_container(app).override.service(IsTestService, new=mocked_foo):
        res = client.get("/foo")
        assert res.status_code == 200
        assert res.json == {"test": "mocked"}
