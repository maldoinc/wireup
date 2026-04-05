import pytest
import wireup.integration.flask
from flask import Flask
from flask.testing import FlaskClient

from test.integration.flask import services as flask_integration_services
from test.integration.flask.async_bp import async_bp
from test.shared import shared_services


def create_async_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(async_bp)

    container = wireup.create_async_container(
        injectables=[shared_services, flask_integration_services],
        config={**app.config, "custom_params": True},
    )
    wireup.integration.flask.setup(container, app)

    return app


@pytest.fixture
def async_app() -> Flask:
    return create_async_app()


@pytest.fixture
def async_client(async_app: Flask):
    return async_app.test_client()


def test_async_app(async_client: FlaskClient) -> None:
    res = async_client.get("/async")
    assert res.status_code == 200
