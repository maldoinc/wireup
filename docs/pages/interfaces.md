# Working with Interfaces

When you're autowiring services, you might want to inject an interface rather than directly
using the concrete implementation. Since Python doesn't have built-in interfaces, 
you can leverage any class that's marked as abstract within the container.

The following code registers `Engine` as an interface. This implies that `Engine` can't be directly injected. 
Instead, you need another service that inherits from it, and that service must also be registered in the container.

```python
@container.abstract
class Engine:
    def do_thing(self):
        ...
```

To autowire interfaces, you can simply register a service that implements the interface within the container. 
When injecting, ask for the interface itself, not its concrete implementation.

```python
@container.register
class CombustionEngine(Engine):
    def do_thing(self):
        return "I'm a Combustion Engine"


@container.autowire
def home(engine: Engine):
    ...
```

In scenarios where there are multiple implementations of an interface, each implementation must be 
associated with a qualifier.

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

While injecting an interface with multiple implementing services, you need to specify a qualifier to indicate 
which concrete class should be resolved.

```python
def home(
    engine: Engine = container.wire(qualifier="electric"),
    combustion: Engine = container.wire(qualifier="combustion"),
):
    ...
```
