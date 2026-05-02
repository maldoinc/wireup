from inspect import Parameter
from typing import Annotated, Any, Optional

import pytest
from wireup import Inject
from wireup.ioc.types import AnnotatedParameter, InjectableQualifier
from wireup.ioc.util import param_get_annotation


def assert_has_qualifier(result: AnnotatedParameter, qualifier_value: str) -> None:
    assert result.annotation is not None
    assert isinstance(result.annotation, InjectableQualifier)
    assert result.annotation.qualifier == qualifier_value


def make_param(annotation: Any) -> Parameter:
    return Parameter(name="test", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=annotation)


class Thing:
    pass


def optional_hint(tp: object) -> object:
    return Optional.__getitem__(tp)


@pytest.mark.parametrize("annotation", [optional_hint(Thing), Thing | None])
def test_optional_basic_type(annotation: Any):
    param = make_param(annotation)
    result = param_get_annotation(param, globalns_supplier=lambda: globals())
    assert result is not None
    assert result.klass == Thing | None
    assert result.annotation is None


@pytest.mark.parametrize(
    "annotation",
    [
        Annotated[optional_hint(Thing), Inject(qualifier="foo")],
        Annotated[Thing | None, Inject(qualifier="foo")],
    ],
)
def test_optional_with_inject(annotation: Any):
    param = make_param(annotation)
    result = param_get_annotation(param, globalns_supplier=lambda: globals())
    assert result is not None
    assert result.klass == Thing | None
    assert_has_qualifier(result, "foo")


@pytest.mark.parametrize(
    "annotation",
    [
        optional_hint(Annotated[Thing, Inject(qualifier="foo")]),
        Annotated[Thing, Inject(qualifier="foo")] | None,
    ],
)
def test_optional_of_annotated(annotation: Any):
    param = make_param(annotation)
    result = param_get_annotation(param, globalns_supplier=lambda: globals())
    assert result is not None
    assert result.klass == Thing | None
    assert_has_qualifier(result, "foo")


def test_non_optional_type():
    param = make_param(Thing)
    result = param_get_annotation(param, globalns_supplier=lambda: globals())
    assert result is not None
    assert result.klass is Thing
    assert result.annotation is None


def test_non_optional_with_inject():
    param = make_param(Annotated[Thing, Inject(qualifier="foo")])
    result = param_get_annotation(param, globalns_supplier=lambda: globals())
    assert result is not None
    assert result.klass is Thing
    assert_has_qualifier(result, "foo")
