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


!!! warning
    You might have noticed the use of `Injected[T]` in the documentation.
    In Wireup's own services, this is not necessary because Wireup assumes ownership of all dependencies for its services.
    However, this may not be the case when injecting into functions, as some arguments might be provided by other decorators or callers.

    When injecting into a function, Wireup uses the `Injected[T]` syntax to explicitly indicate what is being injected.
    This ensures that if the requested dependency is not known, an error is raised instead of silently skipping the parameter.
