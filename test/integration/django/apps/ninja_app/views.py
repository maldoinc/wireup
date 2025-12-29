from ninja import Router, Schema
from wireup import Injected
from wireup.integration.django import inject

from test.shared.shared_services.greeter import AsyncGreeterService, GreeterService


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


router = Router()


@router.get("/greet", response=GreetingResponse)
@inject
def greet_endpoint(
    request,  # noqa: ARG001
    name: str,
    greeter: Injected[GreeterService],
):
    return {"greeting": greeter.greet(name)}


@router.post("/items", response=ItemResponse)
@inject
def create_item_endpoint(
    request,  # noqa: ARG001
    data: ItemSchema,
    greeter: Injected[GreeterService],
):
    return {
        "id": 1,
        "name": data.name,
        "price": data.price,
        "message": greeter.greet(data.name),
    }


@router.get("/no-inject")
def no_inject_endpoint(request, name: str):  # noqa: ARG001
    return {"name": name}


# Async endpoints


@router.get("/async-greet", response=GreetingResponse)
@inject
async def async_greet_endpoint(
    request,  # noqa: ARG001
    name: str,
    greeter: Injected[AsyncGreeterService],
):
    greeting = await greeter.agreet(name)
    return {"greeting": greeting}


@router.post("/async-items", response=ItemResponse)
@inject
async def async_create_item_endpoint(
    request,  # noqa: ARG001
    data: ItemSchema,
    greeter: Injected[AsyncGreeterService],
):
    message = await greeter.agreet(data.name)
    return {
        "id": 1,
        "name": data.name,
        "price": data.price,
        "message": message,
    }
