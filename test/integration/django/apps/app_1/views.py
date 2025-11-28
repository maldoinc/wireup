from django.http import HttpRequest, HttpResponse
from wireup import Injected
from wireup.integration.django import inject
from test.shared.shared_services.greeter import GreeterService
from django.views import View


def test(request: HttpRequest, greeter: Injected[GreeterService]) -> HttpResponse:
    name = request.GET["name"]
    greeting = greeter.greet(name)

    return HttpResponse(f"App 1: {greeting}")


@inject
def test_inject(
    request: HttpRequest, greeter: Injected[GreeterService]
) -> HttpResponse:
    name = request.GET["name"]
    greeting = greeter.greet(name)

    return HttpResponse(f"App 1: {greeting} (with inject decorator)")


class TestInjectView(View):
    @inject
    def get(
        self, request: HttpRequest, greeter: Injected[GreeterService]
    ) -> HttpResponse:
        name = request.GET["name"]
        greeting = greeter.greet(name)

        return HttpResponse(f"App 1: {greeting} (with inject decorator)")
