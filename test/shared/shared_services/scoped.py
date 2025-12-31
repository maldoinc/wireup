from dataclasses import dataclass

from wireup import injectable


@injectable(lifetime="scoped")
class ScopedServiceDependency: ...


@injectable(lifetime="scoped")
@dataclass
class ScopedService:
    other: ScopedServiceDependency
