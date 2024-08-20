from django.http import HttpRequest, HttpResponse
from django.views import View
from typing_extensions import Annotated
from wireup import Inject, container

from test.integration.django.service.greeter_interface import GreeterService
from test.integration.django.service.random_service import RandomService


@container.autowire
def index(
    request: HttpRequest,
    greeter: GreeterService,
    is_debug: Annotated[bool, Inject(param="DEBUG")],
    random_service: RandomService,
) -> HttpResponse:
    name = request.GET.get("name")
    greeting = greeter.greet(name)

    return HttpResponse(f"{greeting}! Debug = {is_debug}. Your lucky number is {random_service.get_random()}")


class RandomNumberView(View):
    @container.autowire
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
        name = request.GET.get("name")
        greeting = self.greeter.greet(name)

        return HttpResponse(
            f"{greeting}! Debug = {self.is_debug}. Your lucky number is {self.random_service.get_random()}"
        )
