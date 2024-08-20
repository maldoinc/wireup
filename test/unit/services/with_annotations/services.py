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
class IFoo(abc.ABC):
    @abc.abstractmethod
    def get_foo(self) -> str:
        raise NotImplementedError


@service
class FooImpl(IFoo):
    def get_foo(self) -> str:
        return "foo"
