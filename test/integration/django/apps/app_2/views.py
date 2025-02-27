from django.http import HttpRequest, HttpResponse

from test.shared.shared_services.greeter import GreeterService


def test(request: HttpRequest, greeter: GreeterService) -> HttpResponse:
    name = request.GET["name"]
    greeting = greeter.greet(name)

    return HttpResponse(f"App 2: {greeting}")
