import inspect
import unittest
from typing import Dict, List, Tuple, Union

from typing_extensions import Annotated
from wireup import Inject
from wireup.ioc.types import AnnotatedParameter, InjectableType, ParameterWrapper, ServiceQualifier
from wireup.ioc.util import (
    is_type_injectable,
    param_get_annotation,
)


class TestUtilityFunctions(unittest.TestCase):
    def test_get_annotated_parameter_retrieves_first_injectable_type(self):
        class Dummy(InjectableType): ...

        d1 = Dummy()
        d2 = Dummy()

        def inner(
            _a: Annotated[str, "ignored", unittest.TestCase, d1],
            _b,
            _c: str,
            _d: Annotated[str, Inject(param="d")],
            _e: str = Inject(param="e"),
            _f=Inject(param="f"),
            _g=d2,
        ): ...

        params = inspect.signature(inner)
        self.assertEqual(
            param_get_annotation(params.parameters["_a"], globalns=globals()), AnnotatedParameter(str, None)
        )
        self.assertEqual(param_get_annotation(params.parameters["_b"], globalns=globals()), None)
        self.assertEqual(
            param_get_annotation(params.parameters["_c"], globalns=globals()), AnnotatedParameter(str, None)
        )
        self.assertEqual(
            param_get_annotation(params.parameters["_d"], globalns=globals()),
            AnnotatedParameter(str, ParameterWrapper("d")),
        )
        self.assertEqual(
            param_get_annotation(params.parameters["_e"], globalns=globals()),
            AnnotatedParameter(str),
        )
        self.assertIsNone(
            param_get_annotation(params.parameters["_f"], globalns=globals()),
        )
        self.assertEqual(param_get_annotation(params.parameters["_g"], globalns=globals()), None)

    def test_is_type_autowireable_basic_types(self):
        self.assertFalse(is_type_injectable(int))
        self.assertFalse(is_type_injectable(float))
        self.assertFalse(is_type_injectable(str))
        self.assertFalse(is_type_injectable(bool))
        self.assertFalse(is_type_injectable(complex))
        self.assertFalse(is_type_injectable(bytes))
        self.assertFalse(is_type_injectable(bytearray))
        self.assertFalse(is_type_injectable(memoryview))

    def test_is_type_autowireable_types_with_typing(self):
        self.assertTrue(is_type_injectable(List[int]))
        self.assertTrue(is_type_injectable(Tuple[str, int]))
        self.assertTrue(is_type_injectable(Dict[str, float]))
        self.assertFalse(is_type_injectable(Union[str, int]))

    def test_is_type_autowireable_non_autowireable_types(self):
        self.assertTrue(is_type_injectable(object))
        self.assertFalse(is_type_injectable(None))
        self.assertFalse(is_type_injectable(Union[str, int, None]))

    def test_annotated_parameter_hash_equality(self):
        self.assertEqual(
            hash(AnnotatedParameter(AnnotatedParameter, ServiceQualifier("wow"))),
            hash(AnnotatedParameter(AnnotatedParameter, ServiceQualifier("wow"))),
        )


class MyCustomClass:
    pass
