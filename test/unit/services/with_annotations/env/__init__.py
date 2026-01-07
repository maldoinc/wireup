from typing_extensions import Annotated
from wireup import Inject, injectable


@injectable
class EnvService:
    def __init__(self, env_name: Annotated[str, Inject(config="env_name")]):
        self.env_name = env_name
