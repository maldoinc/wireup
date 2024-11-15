from dataclasses import dataclass

from wireup import service
from wireup.integration.django import CurrentHttpRequest
from wireup.ioc.types import ServiceLifetime


@service(lifetime=ServiceLifetime.TRANSIENT)
@dataclass
class CurrentDjangoRequest:
    request: CurrentHttpRequest
