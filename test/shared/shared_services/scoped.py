from dataclasses import dataclass

from wireup import ServiceLifetime, service


@service(lifetime=ServiceLifetime.SCOPED)
class ScopedServiceDependency: ...


@service(lifetime=ServiceLifetime.SCOPED)
@dataclass
class ScopedService:
    other: ScopedServiceDependency
