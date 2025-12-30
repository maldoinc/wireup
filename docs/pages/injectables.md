# Injectables

An injectable in Wireup is any class or function decorated with `@injectable`. 
Injectables can live anywhere but must be registered with the container.

For information about registering injectables, see the [Container](container.md#registering-injectables) documentation.

## Class Injectables

The simplest way to define an injectable is with a class:

```python
from wireup import injectable

@injectable
class VehicleRepository: ...

@injectable
class RentalService:
    # VehicleRepository is automatically injected
    def __init__(self, repository: VehicleRepository) -> None: ...
```

## Factory Functions

For complex initialization logic or resource management, wireup supports factories that can handle setup and cleanup operations. See the [Factory Functions](factories.md) documentation for detailed information on creating and using factory functions.

## Dependency Resolution

Wireup uses type annotations to resolve dependencies. Factory name and parameter names are for readability only.

```python
# These are equivalent:
@injectable
def rental_service_factory(repo: VehicleRepository) -> RentalService:
    return RentalService(repo)

@injectable
def make_rental_service(vehicle_store: VehicleRepository) -> RentalService:
    return RentalService(vehicle_store)
```
