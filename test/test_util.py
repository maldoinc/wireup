import unittest

import examples.services
from examples.services.baz_service import BazService
from examples.services.db_service import DbService
from examples.services.foo_service import FooService
from examples.services.random_service import RandomService
from examples.services.truly_random_service import TrulyRandomService
from wireup.ioc.util import (
    find_classes_in_module,
    get_params_with_default_values,
)


class TestUtilityFunctions(unittest.TestCase):
    def test_get_params_with_default_values(self):
        def test_function(_a: int, _b: str = "default", _c: MyCustomClass = None) -> None:
            pass

        params = {name: param.default for name, param in get_params_with_default_values(test_function).items()}
        assert params == {"_b": "default", "_c": None}

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
