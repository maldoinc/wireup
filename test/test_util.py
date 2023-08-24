import unittest

import examples.services
from examples.services.baz_service import BazService
from examples.services.db_service import DbService
from examples.services.foo_service import FooService
from examples.services.random_service import RandomService
from examples.services.truly_random_service import TrulyRandomService
from wireup.ioc.util import (
    find_classes_in_module,
)


class TestUtilityFunctions(unittest.TestCase):
    def test_find_classes_in_package(self):
        self.assertListEqual(
            list(find_classes_in_module(examples.services)),
            [BazService, DbService, FooService, RandomService, TrulyRandomService],
        )

    def test_find_classes_in_package_uses_pattern(self):
        self.assertListEqual(
            list(find_classes_in_module(examples.services, "*Random*")),
            [RandomService, TrulyRandomService],
        )


class MyCustomClass:
    pass
