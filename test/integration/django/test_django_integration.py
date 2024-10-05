import os
import sys
import unittest

import django
from django.test import Client
from django.urls import path
from wireup.integration.django import WireupSettings
from wireup.integration.django.apps import get_container

from test.integration.django import view
from test.integration.django.service.greeter_interface import GreeterService

INSTALLED_APPS = ["wireup.integration.django"]
DEBUG = True
ROOT_URLCONF = sys.modules[__name__]
WIREUP = WireupSettings(service_modules=["test.integration.django.service", "test.integration.django.factory"])
SECRET_KEY = "not_actually_a_secret"  # noqa: S105
START_NUM = 4

urlpatterns = [
    path(r"", view.index),
    path(r"classbased", view.RandomNumberView.as_view()),
]


class TestDjango(unittest.TestCase):
    def setUp(self):
        os.environ["DJANGO_SETTINGS_MODULE"] = "test.integration.django.test_django_integration"
        django.setup()
        self.client = Client()

    def test_django_thing(self):
        res = self.client.get("/?name=World")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode("utf8"), "Hello World! Debug = True. Your lucky number is 4")

    def test_get_random(self):
        res = self.client.get("/classbased?name=Test")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode("utf8"), "Hello Test! Debug = True. Your lucky number is 4")

    def test_override(self):
        class DummyGreeter(GreeterService):
            def greet(self, name: str) -> str:
                return f"Bad day to you, {name}"

        with get_container().override.service(GreeterService, new=DummyGreeter()):
            res = self.client.get("/classbased?name=Test")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode("utf8"), "Bad day to you, Test! Debug = True. Your lucky number is 4")
