from typing_extensions import Annotated
from wireup import Wire, container


@container.register
class EnvService:
    def __init__(self, env_name: Annotated[str, Wire(param="env_name")]):
        self.env_name = env_name
