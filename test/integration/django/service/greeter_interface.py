import abc

from wireup import container


@container.abstract
class GreeterService(abc.ABC):
    @abc.abstractmethod
    def greet(self, name: str) -> str:
        raise NotImplementedError
