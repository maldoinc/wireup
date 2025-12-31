from unittest.mock import MagicMock

import pytest
import wireup.integration.flask
from flask import Flask
from flask.testing import FlaskClient
from wireup.integration.flask import get_app_container

from test.integration.flask import services as flask_integration_services
from test.integration.flask.bp import bp
from test.integration.flask.services.is_test_service import IsTestService
from test.shared import shared_services


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(bp)

    container = wireup.create_sync_container(
        injectables=[shared_services, flask_integration_services],
        config={**app.config, "custom_params": True},
    )
    wireup.integration.flask.setup(container, app)

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


def test_scoped_dependencies(client: FlaskClient) -> None:
    res = client.get("/scoped")
    assert res.status_code == 200
    assert res.json == {}


def test_will_not_autowire_when_no_injections_requested(client: FlaskClient) -> None:
    res = client.get("/not-autowired")
    assert res.data.decode() == "not autowired"


def test_service_depends_on_flask_params(client: FlaskClient) -> None:
    res = client.get("/foo")
    assert res.status_code == 200
    assert res.json == {"test": True}


def test_service_override(client: FlaskClient, app: Flask):
    mocked_foo = MagicMock()
    mocked_foo.is_test = "mocked"

    with get_app_container(app).override.injectable(IsTestService, new=mocked_foo):
        res = client.get("/foo")
        assert res.status_code == 200
        assert res.json == {"test": "mocked"}
