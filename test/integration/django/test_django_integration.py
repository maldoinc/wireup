import sys
import unittest
from test.integration.django.service.greeter_interface import GreeterService

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.test import Client
from django.urls import path
from typing_extensions import Annotated
from wireup import Wire

settings.configure(
    DEBUG=True,
    ROOT_URLCONF=sys.modules[__name__],
    MIDDLEWARE=["wireup.integration.django_integration.WireupMiddleware"],
    WIREUP={"SERVICE_MODULES": ["test.integration.django.service"]},
    SECRET_KEY="secret",
)


def index(
    request: HttpRequest, greeter: GreeterService, is_debug: Annotated[bool, Wire(param="DEBUG")]
) -> HttpResponse:
    name = request.GET.get("name")
    greeting = greeter.greet(name)

    return HttpResponse(f"{greeting}! Debug = {is_debug}")


urlpatterns = [
    path(r"", index),
]


class TestDjango(unittest.TestCase):
    def test_django_thing(self):
        c = Client()
        res = c.get("/?name=World")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode("utf8"), "Hello World! Debug = True")
