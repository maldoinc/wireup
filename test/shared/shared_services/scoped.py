from dataclasses import dataclass

from wireup import service


@service(lifetime="scoped")
class ScopedServiceDependency: ...


@service(lifetime="scoped")
@dataclass
class ScopedService:
    other: ScopedServiceDependency
