from flask import g
from wireup import service


class FlaskG:
    def __init__(self, g):
        self.g = g


@service
def thing() -> FlaskG:
    return FlaskG(g)
