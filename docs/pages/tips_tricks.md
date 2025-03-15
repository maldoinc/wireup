### Reduce init boilerplate

Consider an order processing service that requires multiple dependencies.
Here's how it looks with traditional initialization:

```python title="services/order_processor.py"
@service
class OrderProcessor:
    def __init__(
        self,
        payment_gateway: PaymentGateway,
        inventory_service: InventoryService,
        order_repository: OrderRepository,
    ):
        self.payment_gateway = payment_gateway
        self.inventory_service = inventory_service
        self.order_repository = order_repository
```

Wireup lets you combine the `@service` decorator with dataclasses for a more concise syntax.

```python title="services/order_processor.py"
from dataclasses import dataclass

@service
@dataclass
class OrderProcessor:
    payment_gateway: PaymentGateway
    inventory_service: InventoryService
    order_repository: OrderRepository
```

Using dataclasses eliminates the need to write the `__init__` method and manually assign each dependency, while maintaining
type hints and making the code more maintainable.


### Aliased parameters

If you don't like having string parameters in your service objects you can alias them instead.

```python
def awesome_function(env: Annotated[str, Inject(param="env")]) -> None: ...
def other_awesome_function(env: Annotated[str, Inject(param="env")]) -> None: ...
```

Using type aliases

```python
EnvParameter = Annotated[str, Inject(param="env")]

def awesome_function(env: EnvParameter) -> None: ...
def other_awesome_function(env: EnvParameter) -> None: ...
```