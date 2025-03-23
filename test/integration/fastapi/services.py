from dataclasses import dataclass

from fastapi import Request
from wireup import service


@service(lifetime="scoped")
@dataclass
class ServiceUsingFastapiRequest:
    req: Request
