# Interfaces

When autowiring services it is often desirable to inject an interface rather than the concrete implementation directly.
Since Python does not have interfaces, we can use any class which is marked as abstract in the container.

The following would register `Engine` as an interface. This means that it cannot be injected directly and there must
be another service which inherits it that is also registered in the container for this.

```python
@container.abstract
class Engine:
    def do_thing(self):
        ...
```

To autowire interfaces simply register a service that implements it into the container. 
When injecting ask for the interface rather than the implementation.

```python
@container.register
class CombustionEngine(Engine):
    def do_thing(self):
        return "I'm a Combustion Engine"


@container.autowire
def home(engine: Engine):
    ...
```

For cases where there are multiple implementations, each implementation must be associated with a qualifier.


```python
@container.register(qualifier="electric")
class ElectricEngine(Engine):
    def do_thing(self):
        return "I'm an Electric Engine"


@container.register(qualifier="combustion")
class CombustionEngine(Engine):
    def do_thing(self):
        return "I'm a Combustion Engine"
```

When injecting an interface for which there are multiple services implementing it, a qualifier needs to be used when
injecting the dependency to specify which concrete class should be resolved.

```python
def home(
    engine: Engine = container.wire(qualifier="electric"),
    combustion: Engine = container.wire(qualifier="combustion"),
):
    ...
```
