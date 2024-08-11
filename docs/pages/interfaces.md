Sometimes you might want to inject an interface rather than the concrete implementation directly. 
Since Python doesn't have built-in interfaces, you can use any class marked as abstract.

This method makes testing easier as you can create dummy implementations of these services in your tests
in order to control their behavior.

## Example

The following code registers `Engine` as an interface. This implies that `Engine` can't be directly injected. 
Instead, a dependency that implements the interface must also be registered in the container.

To use interfaces, register a dependency that **directly inherits** the interface 
with the container. When injecting, ask for the interface itself, not the implementations.

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


@container.autowire
def target(engine: Engine):
    engine_type = engine.get_type()  # Returns EngineType.COMBUSTION
    ...
```

## Multiple implementations

If an interface has multiple implementations, associate each of them with a qualifier.
This is essentially a tag used to differentiate between implementations.

```python
@service(qualifier="electric")
class ElectricEngine(Engine):
    def get_type(self):
        return EngineType.ELECTRIC


@service(qualifier="combustion")
class CombustionEngine(Engine):
    def get_type(self) -> EngineType:
        return EngineType.COMBUSTION
```

When injecting an interface with multiple implementing dependencies, you need to specify a qualifier to indicate 
which concrete class should be resolved.

```python
@container.autowire
def target(
    engine: Annotated[Engine, Inject(qualifier="electric")],
    combustion: Annotated[Engine, Inject(qualifier="combustion")],
):
    ...
```


!!! tip
    Qualifiers can be anything hashable, not just strings! For the above example, `EngineType` enum members
    could have been used as qualifiers just as well.

## Default implementation

If there are many implementations associated with a given interface, you may want to associate one of them as the
"default" implementation.

To accomplish that, omit the qualifier when registering the implementation.

```python
@service  # <-- Qualifier being absent will make this the default impl.
class ElectricEngine(Engine):
    pass

@service(qualifier="combustion")
class CombustionEngine(Engine):
    pass
```

In the above example when asking for `Engine` the container will inject `ElectricEngine`. To inject the other implementations 
you need to specify the qualifier as usual.
