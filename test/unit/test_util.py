import functools
import inspect
import unittest
from typing import Callable

import pytest
from typing_extensions import Annotated
from wireup import Inject
from wireup.errors import WireupError
from wireup.ioc.types import (
    AnnotatedParameter,
    ConfigInjectionRequest,
    InjectableQualifier,
    InjectableType,
)
from wireup.ioc.util import (
    get_globals,
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
            _d: Annotated[str, Inject(config="d")],
            _e: str = Inject(config="e"),
            _f=Inject(config="f"),
            _g=d2,
        ): ...

        _param_get_annotation = functools.partial(param_get_annotation, globalns_supplier=lambda: globals())

        params = inspect.signature(inner)
        self.assertEqual(
            _param_get_annotation(params.parameters["_a"]),
            AnnotatedParameter(str, d1),
        )
        self.assertEqual(_param_get_annotation(params.parameters["_b"]), None)
        self.assertEqual(
            _param_get_annotation(params.parameters["_c"]),
            AnnotatedParameter(str, None),
        )
        self.assertEqual(
            _param_get_annotation(params.parameters["_d"]),
            AnnotatedParameter(str, ConfigInjectionRequest("d")),
        )
        self.assertEqual(
            _param_get_annotation(params.parameters["_e"]),
            AnnotatedParameter(str),
        )
        self.assertIsNone(
            _param_get_annotation(params.parameters["_f"]),
        )
        self.assertEqual(_param_get_annotation(params.parameters["_g"]), None)

    def test_annotated_parameter_hash_equality(self):
        self.assertEqual(
            hash(AnnotatedParameter(AnnotatedParameter, InjectableQualifier("wow"))),
            hash(AnnotatedParameter(AnnotatedParameter, InjectableQualifier("wow"))),
        )


def test_raises_multiple_annotations() -> None:
    def inner(_a: Annotated[str, Inject(), Inject(config="foo")]): ...

    params = inspect.signature(inner)

    with pytest.raises(WireupError, match="Multiple Wireup annotations used"):
        param_get_annotation(params.parameters["_a"], globalns_supplier=globals())


class MyCustomClass:
    pass


def _sample_function():
    pass


def test_returns_globals_for_class():
    # GIVEN
    cls = MyCustomClass

    # WHEN
    result = get_globals(cls)

    # THEN
    assert "_sample_function" in result
    assert "MyCustomClass" in result


@pytest.mark.parametrize(
    "partial_func",
    (
        _sample_function,
        functools.partial(_sample_function),
        functools.partial(functools.partial(functools.partial(_sample_function))),
    ),
)
def test_unwraps_functools_partial(partial_func: Callable):
    # GIVEN
    # WHEN
    result = get_globals(partial_func)

    # THEN
    assert result is _sample_function.__globals__
