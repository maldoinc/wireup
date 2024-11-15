from django.http import HttpRequest, HttpResponse
from django.views import View
from typing_extensions import Annotated
from wireup import Inject

from test.integration.django.service.current_request_service import CurrentDjangoRequest
from test.integration.django.service.greeter_interface import GreeterService
from test.integration.django.service.random_service import RandomService


def index(
    _: HttpRequest,
    example_request_service: CurrentDjangoRequest,
    greeter: GreeterService,
    is_debug: Annotated[bool, Inject(param="DEBUG")],
    random_service: RandomService,
) -> HttpResponse:
    name = example_request_service.request.GET["name"]
    greeting = greeter.greet(name)

    return HttpResponse(f"{greeting}! Debug = {is_debug}. Your lucky number is {random_service.get_random()}")


class RandomNumberView(View):
    def __init__(
        self,
        greeter: GreeterService,
        is_debug: Annotated[bool, Inject(param="DEBUG")],
        random_service: RandomService,
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
