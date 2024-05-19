import inspect
import unittest
from typing import Dict, List, Tuple, Union

from typing_extensions import Annotated
from wireup import Inject
from wireup.ioc.types import AnnotatedParameter, ContainerProxyQualifier, InjectableType, ParameterWrapper
from wireup.ioc.util import (
    is_type_autowireable,
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
        self.assertEqual(param_get_annotation(params.parameters["_a"]), AnnotatedParameter(str, None))
        self.assertEqual(param_get_annotation(params.parameters["_b"]), None)
        self.assertEqual(param_get_annotation(params.parameters["_c"]), AnnotatedParameter(str, None))
        self.assertEqual(param_get_annotation(params.parameters["_d"]), AnnotatedParameter(str, ParameterWrapper("d")))
        self.assertEqual(param_get_annotation(params.parameters["_e"]), AnnotatedParameter(str, ParameterWrapper("e")))
        self.assertEqual(param_get_annotation(params.parameters["_f"]), AnnotatedParameter(None, ParameterWrapper("f")))
        self.assertEqual(param_get_annotation(params.parameters["_g"]), AnnotatedParameter(None, d2))

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

    def test_annotated_parameter_hash_equality(self):
        self.assertEqual(
            hash(AnnotatedParameter(AnnotatedParameter, ContainerProxyQualifier("wow"))),
            hash(AnnotatedParameter(AnnotatedParameter, ContainerProxyQualifier("wow"))),
        )


class MyCustomClass:
    pass
