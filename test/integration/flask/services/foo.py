from dataclasses import dataclass

from typing_extensions import Annotated
from wireup import Inject, service
from wireup.ioc.types import ServiceLifetime


@service
@dataclass
class IsTestService:
    is_test: Annotated[bool, Inject(param="TESTING")]


@service(lifetime=ServiceLifetime.SCOPED)
class ScopedServiceDependency: ...


@service(lifetime=ServiceLifetime.SCOPED)
@dataclass
class ScopedService:
    other: ScopedServiceDependency
