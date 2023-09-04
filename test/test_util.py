import unittest

from test import services
from test.services.baz_service import BazService
from test.services.db_service import DbService
from test.services.foo_service import FooService
from test.services.random_service import RandomService
from test.services.truly_random_service import TrulyRandomService
from wireup.ioc.util import (
    find_classes_in_module,
)


class TestUtilityFunctions(unittest.TestCase):
    def test_find_classes_in_package(self):
        self.assertListEqual(
            list(find_classes_in_module(services)),
            [BazService, DbService, FooService, RandomService, TrulyRandomService],
        )

    def test_find_classes_in_package_uses_pattern(self):
        self.assertListEqual(
            list(find_classes_in_module(services, "*Random*")),
            [RandomService, TrulyRandomService],
        )


class MyCustomClass:
    pass
