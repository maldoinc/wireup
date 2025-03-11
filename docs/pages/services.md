In Wireup, services are decorated classes or functions that produce a result when called. To define a service
you must use the `@service` decorator on a class or a function that produces the desired dependency.

Wireup does not enforce a code structure. Services may live anywhere, but must be registered with the container. 
To do that, the modules where services reside must be passed to the `service_modules` argument in the 
`wireup.create_container` or `wireup.create_async_container` call.

!!! tip "Good to know"
    You don't need to register each module separately, only the top level modules are sufficient
    as the container will perform a recursive scan.

## Class-based services

Services in Wireup can be defined using class-based or factory-based approaches. For class-based services, 
use the `@service` decorator on your class definition.

```python
from wireup import service

@service
class Foo:
    def __init__(self) -> None:
        pass

@service
class Bar:
    def __init__(self, foo: Foo) -> None:
        # Wireup automatically injects the Foo instance
        self.foo = foo
```

## Factory-based services

For more complex initialization scenarios, you can use factory functions. These are regular functions
decorated with `@service` that construct and return service instances. The function must include a return
type annotation to tell Wireup what type of service it creates.

```python
from wireup import service

@service
def create_bar(foo: Foo) -> Bar:
    # Custom initialization logic here
    return Bar(foo)
```

## Dependency injection

Wireup uses type annotations for dependency resolution.
Choose descriptive parameter names for readability, but know that they don't affect
how dependencies are resolved. The following factory definitions are equivalent:

```python
# These factory functions are functionally identical:

@service
def create_bar(foo: Foo) -> Bar:
    return Bar(foo)

@service
def create_bar(foo_dependency: Foo) -> Bar:
    return Bar(foo_dependency)
```