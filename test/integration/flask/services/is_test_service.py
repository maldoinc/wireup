from dataclasses import dataclass

from typing_extensions import Annotated
from wireup import Inject, service


@service
@dataclass
class IsTestService:
    is_test: Annotated[bool, Inject(config="TESTING")]
