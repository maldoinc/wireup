from django.http import HttpRequest, HttpResponse
from django.views import View
from typing_extensions import Annotated
from wireup import Inject, Injected

from test.integration.django.injectable.current_request_service import CurrentDjangoRequest
from test.integration.django.injectable.random_service import RandomService
from test.shared.shared_services.greeter import AsyncGreeterService, GreeterService


def index(
    _request: HttpRequest,
    example_request_service: Injected[CurrentDjangoRequest],
    greeter: Injected[GreeterService],
    is_debug: Annotated[bool, Inject(config="DEBUG")],
    random_service: Injected[RandomService],
) -> HttpResponse:
    name = example_request_service.request.GET["name"]
    greeting = greeter.greet(name)

    return HttpResponse(f"{greeting}! Debug = {is_debug}. Your lucky number is {random_service.get_random()}")


class RandomNumberView(View):
    def __init__(
        self,
        greeter: Injected[GreeterService],
        is_debug: Annotated[bool, Inject(config="DEBUG")],
        random_service: Injected[RandomService],
    ) -> None:
        self.random_service = random_service
        self.is_debug = is_debug
        self.greeter = greeter

    def get(
        self,
        request: HttpRequest,
    ) -> HttpResponse:
        name = request.GET["name"]
        greeting = self.greeter.greet(name)

        return HttpResponse(
            f"{greeting}! Debug = {self.is_debug}. Your lucky number is {self.random_service.get_random()}"
        )


class AsyncRandomNumberView(View):
    def __init__(
        self,
        greeter: Injected[AsyncGreeterService],
        is_debug: Annotated[bool, Inject(config="DEBUG")],
        random_service: Injected[RandomService],
    ) -> None:
        self.random_service = random_service
        self.is_debug = is_debug
        self.greeter = greeter

    async def get(
        self,
        request: HttpRequest,
    ) -> HttpResponse:
        name = request.GET["name"]
        greeting = await self.greeter.agreet(name)

        return HttpResponse(
            f"{greeting}! Debug = {self.is_debug}. Your lucky number is {self.random_service.get_random()}"
        )


async def async_greet(
    request: HttpRequest,
    greeter: Injected[AsyncGreeterService],
    is_debug: Annotated[bool, Inject(config="DEBUG")],
) -> HttpResponse:
    """Async view that uses an async injectable."""
    name = request.GET["name"]
    greeting = await greeter.agreet(name)
    return HttpResponse(f"{greeting}! Debug = {is_debug}")
