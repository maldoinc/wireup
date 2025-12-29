from dataclasses import dataclass

from django.http import HttpRequest
from wireup import injectable


@injectable(lifetime="scoped")
@dataclass
class CurrentDjangoRequest:
    request: HttpRequest
