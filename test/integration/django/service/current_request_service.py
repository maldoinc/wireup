from dataclasses import dataclass

from django.http import HttpRequest
from wireup import service


@service(lifetime="scoped")
@dataclass
class CurrentDjangoRequest:
    request: HttpRequest
