import os
from dataclasses import dataclass
from typing import List

from flask import Blueprint, Flask, Response, jsonify
from wireup import container
from wireup.ioc.parameter import TemplatedString

import examples
from examples.services.baz_service import BazService
from examples.services.db_service import DbService
from examples.services.foo_service import FooService


@container.abstract
class Engine:
    def do_thing(self):
        ...


@container.register(qualifier="electric")
class ElectricEngine(Engine):
    def do_thing(self):
        return "Hi from Electric Engine"


@container.register(qualifier="combustion")
class CombustionEngine(Engine):
    def do_thing(self):
        return "Hi from Combustion Engine"


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
        engine: Engine = container.wire(qualifier="electric"),
        combustion: Engine = container.wire(qualifier="combustion"),
        env: str = container.wire(param="env"),
    ) -> Response:
        return jsonify(
            {
                "engine": engine.do_thing(),
                "combustion": combustion.do_thing(),
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
                from_address="aldo.mateli@gmail.com", to_addresses=["aldo.mateli@yahoo.com", "aldo.mateli@outlook.com"],
            ),
        },
    )
    container.params.update(os.environ)
    container.register_all_in_module(examples.services)
    container.initialization_context.update(
        DbService,
        {
            "connection_str": "connection_str",
            "cache_dir": TemplatedString("${cache_dir}/${USER}/db"),
        },
    )

    app.register_blueprint(HomeBlueprint.bp)
    app.run()
