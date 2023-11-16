import inspect
import unittest
from typing import Dict, List, Tuple, Union

from typing_extensions import Annotated
from wireup.ioc.types import AnnotatedParameter
from wireup.ioc.util import (
    is_type_autowireable,
    parameter_get_type_and_annotation,
)


class TestUtilityFunctions(unittest.TestCase):
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

    def test_is_type_autowireable_basic_types(self):
        self.assertFalse(is_type_autowireable(int))
        self.assertFalse(is_type_autowireable(float))
        self.assertFalse(is_type_autowireable(str))
        self.assertFalse(is_type_autowireable(bool))
        self.assertFalse(is_type_autowireable(complex))
        self.assertFalse(is_type_autowireable(bytes))
        self.assertFalse(is_type_autowireable(bytearray))
        self.assertFalse(is_type_autowireable(memoryview))

    def test_is_type_autowireable_types_with_typing(self):
        self.assertTrue(is_type_autowireable(List[int]))
        self.assertTrue(is_type_autowireable(Tuple[str, int]))
        self.assertTrue(is_type_autowireable(Dict[str, float]))
        self.assertFalse(is_type_autowireable(Union[str, int]))

    def test_is_type_autowireable_non_autowireable_types(self):
        self.assertTrue(is_type_autowireable(object))
        self.assertFalse(is_type_autowireable(None))
        self.assertFalse(is_type_autowireable(Union[str, int, None]))


class MyCustomClass:
    pass
