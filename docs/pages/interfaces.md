When autowiring dependencies, you might want to inject an interface rather than 
the concrete implementation directly. Since Python doesn't have built-in interfaces, you can leverage any class 
that's marked as abstract within the container.

This method helps to make testing easier as you can create dummy implementations of these services in your tests
in order to control their behavior.

## Example

The following code registers `Engine` as an interface. This implies that `Engine` can't be directly injected. 
Instead, a dependency that implements the interface must be present and also be registered in the container.

To autowire interfaces, register a dependency that **directly inherits** the interface 
within the container. When injecting, ask for the interface itself, not any of the implementations.

```python
@container.abstract
class Engine(abc.ABC):
    def get_type(self) -> EngineType:
        raise NotImplementedError()
    
    
@container.register
class CombustionEngine(Engine):
    @override
    def get_type(self) -> EngineType:
        return EngineType.COMBUSTION


@container.autowire
def target(engine: Engine):
    engine_type = engine.get_type() # Returns EngineType.COMBUSTION
    ...
```

### Multiple implementations

In scenarios where there are multiple implementations of an interface, each implementation must be 
associated with a qualifier.

```python
@container.register(qualifier="electric")
class ElectricEngine(Engine):
    @override
    def get_type(self):
        return EngineType.ELECTRIC


@container.register(qualifier="combustion")
class CombustionEngine(Engine):
    @override
    def get_type(self) -> EngineType:
        return EngineType.COMBUSTION
```

When injecting an interface with multiple implementing dependencies, you need to specify a qualifier to indicate 
which concrete class should be resolved.

```python
container.autowire
def target(
    engine: Annotated[Engine, Wire(qualifier="electric")],
    combustion: Annotated[Engine, Wire(qualifier="combustion")],
):
    ...
```


!!! tip
    Qualifiers can be anything, not just strings! For the above example, `EngineType` enum members
    could have been used as qualifiers just as well.

## Default implementation

When there are many implementations associated with a given interface you may want to associate one of them as the
"default" implementation. This means that the container will inject that when there is no qualifier specified
even though there are multiple implementations registered.

To achieve that simply do not set the qualifier for that implementation when registering it.

```python
@container.register  # <-- Qualifier being absent will make this the default impl.
class ElectricEngine(Engine):
    pass

@container.register(qualifier="combustion")
class CombustionEngine(Engine):
    pass
```

In the above example when asking for `Engine` the container will inject `ElectricEngine`. For the rest of the 
implementations you need to specify the qualifier as usual.
