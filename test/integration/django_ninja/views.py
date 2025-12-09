from typing import Annotated

from ninja import Router, Schema
from wireup import Inject, Injected
from wireup.integration.django.ninja import inject

from test.shared.shared_services.greeter import GreeterService


# --- Schemas ---
class ItemSchema(Schema):
    name: str
    price: float


class ItemResponse(Schema):
    id: int
    name: str
    price: float
    message: str


class GreetingResponse(Schema):
    greeting: str
    debug: bool


# --- Django Ninja Router ---
router = Router()


@router.get("/greet", response=GreetingResponse)
@inject
def greet_endpoint(
    request,  # noqa: ARG001
    name: str,
    greeter: Injected[GreeterService],
    is_debug: Annotated[bool, Inject(param="DEBUG")],
):
    return {"greeting": greeter.greet(name), "debug": is_debug}


@router.post("/items", response=ItemResponse)
@inject
def create_item_endpoint(
    request,  # noqa: ARG001
    data: ItemSchema,
    greeter: Injected[GreeterService],
):
    # Demonstrates that both Body param (data) and injected service work together
    return {
        "id": 1,
        "name": data.name,
        "price": data.price,
        "message": greeter.greet(data.name),
    }


@router.get("/multi-inject")
@inject
def multi_inject_endpoint(
    request,  # noqa: ARG001
    greeter: Injected[GreeterService],
    is_debug: Annotated[bool, Inject(param="DEBUG")],
    secret_key: Annotated[str, Inject(param="SECRET_KEY")],
):
    # Demonstrates multiple injectable params
    return {
        "greeting": greeter.greet("World"),
        "debug": is_debug,
        "has_secret": len(secret_key) > 0,
    }


@router.get("/no-inject")
def no_inject_endpoint(request, name: str):  # noqa: ARG001
    # A route without any injection - should work normally
    return {"name": name}

