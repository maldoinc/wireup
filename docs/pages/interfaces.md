# Interface Injection

You can use protocols, abstract classes, or even regular classes as interfaces when you need to inject dependencies. This pattern is particularly useful for testing, as it allows you to create mock implementations or easily swap implementations.

## Basic Usage

You can use `as_type` to register a service as *any* type, such as a `Protocol`, an Abstract Base Class, or even another regular class.

Define a `Protocol` and register concrete classes that implement it using `@injectable(as_type=...)`.

```python
from wireup import container, injectable
from typing import Protocol


class Engine(Protocol):
    def get_type(self) -> str: ...


@injectable(as_type=Engine)
class CombustionEngine:
    def get_type(self) -> str:
        return "combustion"


@wireup.inject_from_container(container)
def target(engine: Engine):
    engine_type = engine.get_type()  # Returns "combustion"
```

## Multiple Implementations

Use qualifiers to distinguish between different implementations of the same interface:

```python
@injectable(as_type=Engine, qualifier="electric")
class ElectricEngine:
    def get_type(self):
        return "electric"


@injectable(as_type=Engine, qualifier="combustion")
class CombustionEngine:
    def get_type() -> str:
        return "combustion"


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
@injectable(as_type=Engine)  # Default implementation
class ElectricEngine:
    pass

@injectable(as_type=Engine, qualifier="combustion")
class CombustionEngine:
    pass
```

When injecting `Engine` without a qualifier, the container will use the default implementation (`ElectricEngine` in this example). Use qualifiers to access other implementations.

## Optional Binding

When using factories that return an optional type (e.g. `T | None`), `as_type` will automatically be registered as optional as well.

```python
@injectable(as_type=Engine)
def make_engine() -> CombustionEngine | None:
    # ...
```

This acts as if the factory was registered with `as_type=Engine | None`, allowing you to inject `Engine | None` or `Optional[Engine]`.
