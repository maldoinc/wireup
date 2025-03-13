# Services

A service in Wireup is any class or function decorated with `@service`. 
While services can live in any module, their containing modules must be registered with the container via `service_modules` when calling `wireup.create_sync_container` or `wireup.create_async_container`.

You also don't need to register each module separately, only the top level modules are sufficient
as the container will perform a recursive scan.

## Class Services

The simplest way to define a service is with a class:

```python
from wireup import service

@service
class VehicleRepository: ...

@service
class RentalService:
    # VehicleRepository is automatically injected
    def __init__(self, repository: VehicleRepository) -> None: ...
```

## Factory Services

For complex initialization, use factories. These are regular functions
decorated with `@service` that construct and return service instances. The function must include a return
type annotation denote what type of service it creates.

```python
@service
def create_payment_processor(
    api_key: Annotated[str, Inject(param="STRIPE_API_KEY")]
) -> PaymentProcessor:
    processor = PaymentProcessor()
    processor.configure(api_key)

    return processor
```

You can now inject `PaymentProcessor` as usual.

## Dependency Resolution

Wireup uses type annotations to resolve dependencies. Parameter names are for readability only:

```python
# These are equivalent:
@service
def create_rental_service(repo: VehicleRepository) -> RentalService:
    return RentalService(repo)

@service
def create_rental_service(vehicle_store: VehicleRepository) -> RentalService:
    return RentalService(vehicle_store)
```