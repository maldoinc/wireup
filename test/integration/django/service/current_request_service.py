from dataclasses import dataclass

from django.http import HttpRequest
from wireup import service
from wireup.ioc.types import ServiceLifetime


@service(lifetime=ServiceLifetime.TRANSIENT)
@dataclass
class CurrentDjangoRequest:
    request: HttpRequest
