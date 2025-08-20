import inspect
import unittest

import pytest
from typing_extensions import Annotated
from wireup import Inject
from wireup.errors import WireupError
from wireup.ioc.types import AnnotatedParameter, InjectableType, ParameterWrapper, ServiceQualifier
from wireup.ioc.util import (
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
        self.assertEqual(param_get_annotation(params.parameters["_a"], globalns=globals()), AnnotatedParameter(str, d1))
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

    def test_annotated_parameter_hash_equality(self):
        self.assertEqual(
            hash(AnnotatedParameter(AnnotatedParameter, ServiceQualifier("wow"))),
            hash(AnnotatedParameter(AnnotatedParameter, ServiceQualifier("wow"))),
        )


def test_raises_multiple_annotations() -> None:
    def inner(_a: Annotated[str, Inject(), Inject(param="foo")]): ...

    params = inspect.signature(inner)

    with pytest.raises(WireupError, match="Multiple Wireup annotations used"):
        param_get_annotation(params.parameters["_a"], globalns=globals())


class MyCustomClass:
    pass
