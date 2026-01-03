from dataclasses import dataclass

from typing_extensions import Annotated
from wireup import Inject, injectable


@injectable
@dataclass
class IsTestService:
    is_test: Annotated[bool, Inject(config="TESTING")]
