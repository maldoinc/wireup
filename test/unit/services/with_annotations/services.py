import abc

from typing_extensions import Annotated
from wireup import Inject, Injected, abstract, injectable

from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.no_annotations.random.truly_random_service import TrulyRandomService


@injectable(qualifier="foo")
def random_service_factory() -> RandomService:
    return RandomService()


@injectable(qualifier="foo")
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


@injectable
class FooImpl(Foo):
    def get_foo(self) -> str:
        return "foo"


@injectable(qualifier="other")
class OtherFooImpl(Foo):
    def get_foo(self) -> str:
        return "other foo"


@injectable
class FooImplWithInjected:
    def __init__(self, foo: Injected[Foo]) -> None:
        self.foo = foo


@injectable(lifetime="scoped")
class ScopedService: ...


@injectable(lifetime="transient")
class TransientService: ...
