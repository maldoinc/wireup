from dataclasses import dataclass

from fastapi import Request
from wireup.annotation import service
from wireup.ioc.types import ServiceLifetime


@service(lifetime=ServiceLifetime.SCOPED)
@dataclass
class ServiceUsingFastapiRequest:
    req: Request
