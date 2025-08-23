from inspect import Parameter
from typing import Any, Optional

from typing_extensions import Annotated
from wireup import Inject
from wireup.ioc.types import AnnotatedParameter, ServiceQualifier
from wireup.ioc.util import param_get_annotation


def assert_has_qualifier(result: AnnotatedParameter, qualifier_value: str) -> None:
    assert result.annotation is not None
    assert isinstance(result.annotation, ServiceQualifier)
    assert result.annotation.qualifier == qualifier_value


def make_param(annotation: Any) -> Parameter:
    return Parameter(name="test", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=annotation)


class Thing:
    pass


def test_optional_basic_type():
    param = make_param(Optional[Thing])
    result = param_get_annotation(param, globalns=globals())
    assert result is not None
    assert result.klass is Thing
    assert result.annotation is None


def test_optional_with_inject():
    param = make_param(Annotated[Optional[Thing], Inject(qualifier="foo")])
    result = param_get_annotation(param, globalns=globals())
    assert result is not None
    assert result.klass is Thing
    assert_has_qualifier(result, "foo")


def test_optional_of_annotated():
    param = make_param(Optional[Annotated[Thing, Inject(qualifier="foo")]])
    result = param_get_annotation(param, globalns=globals())
    assert result is not None
    assert result.klass is Thing
    assert_has_qualifier(result, "foo")


def test_non_optional_type():
    param = make_param(Thing)
    result = param_get_annotation(param, globalns=globals())
    assert result is not None
    assert result.klass is Thing
    assert result.annotation is None


def test_non_optional_with_inject():
    param = make_param(Annotated[Thing, Inject(qualifier="foo")])
    result = param_get_annotation(param, globalns=globals())
    assert result is not None
    assert result.klass is Thing
    assert_has_qualifier(result, "foo")
