# Flask example

```python
import os
import examples
from dataclasses import dataclass

from wireup.ioc.container_util import ParameterWrapper
from wireup.ioc.parameter import TemplatedString
from examples.services.baz_service import BazService
from examples.services.db_service import DbService
from examples.services.foo_service import FooService
from typing import List

from flask import Blueprint, Flask, Response, jsonify
from wireup import container


@dataclass
class MailerConfig:
    from_address: str
    to_addresses: List[str]


app = Flask(__name__)


class HomeBlueprint:
    bp = Blueprint("home", __name__)

    @staticmethod
    @bp.route("/<name>")
    @container.autowire
    def home(
            name: str,
            foo: FooService,
            baz: BazService,
            env: str = wire(param="env"),
    ) -> Response:
        return jsonify(
            {
                "foo": foo.bar(),
                "name": name,
                "env": env,
                "baz": baz.baz(),
            },
        )


if __name__ == "__main__":
    container.params.update(
        {
            "connection_str": "sqlite://memory",
            "env": "dev",
            "cache_dir": "/var/cache",
            "mailer_config": MailerConfig(
                from_address="aldo.mateli@gmail.com", to_addresses=["aldo.mateli@yahoo.com", "aldo.mateli@outlook.com"]
            ),
        }
    )
    container.params.update(os.environ)
    container.register_all_in_module(examples.services)

    container.initialization_context.update(DbService, {
        "connection_str": ParameterWrapper("connection_str"),
        "cache_dir": ParameterWrapper(TemplatedString("${cache_dir}/${USER}/db")),
    }
                                            )

    app.register_blueprint(HomeBlueprint.bp)
    app.run()

```