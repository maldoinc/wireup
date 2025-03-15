# Interface Injection

You can use abstract classes as interfaces when you need to inject abstract dependencies. This pattern is particularly useful for testing, as it allows you to create mock implementations.

## Basic Usage

Register an abstract class as an interface using the `@abstract` decorator. Then implement and register concrete classes that inherit from it.

```python
from wireup import abstract, container, service


@abstract
class Engine(abc.ABC):
    @abc.abstractmethod
    def get_type(self) -> EngineType:
        raise NotImplementedError


@service
class CombustionEngine(Engine):
    @override
    def get_type(self) -> EngineType:
        return EngineType.COMBUSTION


@wireup.inject_from_container(container)
def target(engine: Engine):
    engine_type = engine.get_type()  # Returns EngineType.COMBUSTION
```

## Multiple Implementations

Use qualifiers to distinguish between different implementations of the same interface:

```python
@service(qualifier="electric")
class ElectricEngine(Engine):
    def get_type(self):
        return EngineType.ELECTRIC


@service(qualifier="combustion")
class CombustionEngine(Engine):
    def get_type() -> EngineType:
        return EngineType.COMBUSTION


@wireup.inject_from_container(container)
def target(
    electric: Annotated[Engine, Inject(qualifier="electric")],
    combustion: Annotated[Engine, Inject(qualifier="combustion")],
):
    ...
```

!!! tip
    Qualifiers can be any hashable value, including enum members.

## Default Implementation

To set a default implementation, register one class without a qualifier:

```python
@service  # Default implementation
class ElectricEngine(Engine):
    pass

@service(qualifier="combustion")
class CombustionEngine(Engine):
    pass
```

When injecting `Engine` without a qualifier, the container will use the default implementation (`ElectricEngine` in this example). Use qualifiers to access other implementations.
