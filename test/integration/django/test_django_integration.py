import os
import sys
import unittest
from test.integration.django import view

import django
from django.test import Client
from django.urls import path

INSTALLED_APPS = ["wireup.integration.django"]
DEBUG = True
ROOT_URLCONF = sys.modules[__name__]
WIREUP = {"SERVICE_MODULES": ["test.integration.django.service", "test.integration.django.factory"]}
SECRET_KEY = "secret"
START_NUM = 4

urlpatterns = [
    path(r"", view.index),
    path(r"classbased", view.RandomNumberView.as_view()),
]


class TestDjango(unittest.TestCase):
    def setUp(self):
        os.environ["DJANGO_SETTINGS_MODULE"] = "test.integration.django.test_django_integration"
        django.setup()

    def test_django_thing(self):
        c = Client()
        res = c.get("/?name=World")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode("utf8"), "Hello World! Debug = True. Your lucky number is 4")

    def test_get_random(self):
        c = Client()
        res = c.get("/classbased?name=Test")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode("utf8"), "Hello Test! Debug = True. Your lucky number is 4")
