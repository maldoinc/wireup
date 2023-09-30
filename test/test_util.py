import inspect
import unittest
from typing_extensions import Annotated

from test import services
from test.services.baz_service import BazService
from test.services.db_service import DbService
from test.services.foo_service import FooService
from test.services.random_service import RandomService
from test.services.truly_random_service import TrulyRandomService
from wireup.ioc.util import (
    find_classes_in_module,
    parameter_get_type_and_annotation,
)
from wireup.ioc.types import AnnotatedParameter


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

    def test_get_annotated_parameter(self):
        class Dummy:
            ...

        d1 = Dummy()
        d2 = Dummy()

        def inner(_a: Annotated[str, d1], _b, _c: str, _d=d2):
            ...

        params = inspect.signature(inner)
        self.assertEqual(parameter_get_type_and_annotation(params.parameters["_a"]), AnnotatedParameter(str, d1))
        self.assertEqual(parameter_get_type_and_annotation(params.parameters["_b"]), AnnotatedParameter(None, None))
        self.assertEqual(parameter_get_type_and_annotation(params.parameters["_c"]), AnnotatedParameter(str, None))
        self.assertEqual(parameter_get_type_and_annotation(params.parameters["_d"]), AnnotatedParameter(None, d2))


class MyCustomClass:
    pass
