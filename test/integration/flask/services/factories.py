from flask import g
from wireup import service

from test.fixtures import FooBar, FooBase
from test.unit.services.no_annotations.random.random_service import RandomService


class FlaskG:
    def __init__(self, g):
        self.g = g


@service
def thing() -> FlaskG:
    return FlaskG(g)


@service
def random_factory() -> RandomService:
    return RandomService()


@service
def foo_factory() -> FooBase:
    return FooBar()
