from typing_extensions import Annotated
from wireup import Inject, service


@service
class EnvService:
    def __init__(self, env_name: Annotated[str, Inject(param="env_name")]):
        self.env_name = env_name
