from flask import g
from wireup import injectable


class FlaskG:
    def __init__(self, g):
        self.g = g


@injectable
def thing() -> FlaskG:
    return FlaskG(g)
