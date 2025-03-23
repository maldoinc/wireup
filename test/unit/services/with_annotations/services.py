import abc

from typing_extensions import Annotated
from wireup import Inject, abstract, service

from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.no_annotations.random.truly_random_service import TrulyRandomService


@service(qualifier="foo")
def random_service_factory() -> RandomService:
    return RandomService()


@service(qualifier="foo")
def truly_random_service_factory(
    random_service: Annotated[RandomService, Inject(qualifier="foo")],
) -> TrulyRandomService:
    return TrulyRandomService(random_service)


@abstract
class Foo(abc.ABC):
    @abc.abstractmethod
    def get_foo(self) -> str:
        raise NotImplementedError


@abstract
class InterfaceWithoutImpls(abc.ABC):
    @abc.abstractmethod
    def noop(self) -> str:
        raise NotImplementedError


@service
class FooImpl(Foo):
    def get_foo(self) -> str:
        return "foo"


@service(qualifier="other")
class OtherFooImpl(Foo):
    def get_foo(self) -> str:
        return "other foo"


@service(lifetime="scoped")
class ScopedService: ...


@service(lifetime="transient")
class TransientService: ...
