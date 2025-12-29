from __future__ import annotations

import typing
from typing import Optional

import pytest
from typing_extensions import Annotated
from wireup.ioc.type_analysis import TypeAnalysis, analyze_type


@pytest.mark.parametrize(
    "type_hint, expected",
    [
        (int, TypeAnalysis(normalized_type=int, raw_type=int, is_optional=False, annotations=())),
        (str, TypeAnalysis(normalized_type=str, raw_type=str, is_optional=False, annotations=())),
    ],
)
def test_analyze_basic_types(type_hint: type, expected: TypeAnalysis) -> None:
    res: TypeAnalysis = analyze_type(type_hint)

    assert res == expected


@pytest.mark.parametrize(
    "type_hint, expected",
    [
        (Optional[int], TypeAnalysis(normalized_type=Optional[int], raw_type=int, is_optional=True, annotations=())),
        (Optional[str], TypeAnalysis(normalized_type=Optional[str], raw_type=str, is_optional=True, annotations=())),
    ],
)
def test_analyze_optional_types(type_hint: type, expected: TypeAnalysis) -> None:
    res: TypeAnalysis = analyze_type(type_hint)

    assert res == expected


@pytest.mark.parametrize(
    "type_hint, expected",
    [
        (
            typing.Union[int, str, None],
            TypeAnalysis(
                normalized_type=typing.Optional[typing.Union[int, str]],
                raw_type=typing.Union[int, str],
                is_optional=True,
                annotations=(),
            ),
        ),
    ],
)
def test_analyze_union_with_none_multiple_types(type_hint: type, expected: TypeAnalysis) -> None:
    res: TypeAnalysis = analyze_type(type_hint)

    assert res == expected


@pytest.mark.parametrize(
    "type_hint, expected",
    [
        (
            Annotated[int, "meta", 123],
            TypeAnalysis(normalized_type=int, raw_type=int, is_optional=False, annotations=("meta", 123)),
        ),
        (Annotated[str, "x"], TypeAnalysis(normalized_type=str, raw_type=str, is_optional=False, annotations=("x",))),
    ],
)
def test_analyze_annotated_plain(type_hint: type, expected: TypeAnalysis) -> None:
    res: TypeAnalysis = analyze_type(type_hint)

    assert res == expected


@pytest.mark.parametrize(
    "type_hint, expected",
    [
        (
            Annotated[Optional[int], "a"],
            TypeAnalysis(normalized_type=Optional[int], raw_type=int, is_optional=True, annotations=("a",)),
        ),
        (
            Optional[Annotated[int, "b"]],
            TypeAnalysis(normalized_type=Optional[int], raw_type=int, is_optional=True, annotations=("b",)),
        ),
    ],
)
def test_analyze_annotated_optional_variants(type_hint: type, expected: TypeAnalysis) -> None:
    res: TypeAnalysis = analyze_type(type_hint)
    assert res == expected


@pytest.mark.parametrize(
    "type_hint, expected",
    [
        (
            Annotated[Annotated[int, "inner"], "outer"],
            TypeAnalysis(normalized_type=int, raw_type=int, is_optional=False, annotations=("inner", "outer")),
        ),
        (
            Annotated[Annotated[Annotated[int, "a"], "b"], "c"],
            TypeAnalysis(normalized_type=int, raw_type=int, is_optional=False, annotations=("a", "b", "c")),
        ),
    ],
)
def test_analyze_nested_annotated_ordering(type_hint: type, expected: TypeAnalysis) -> None:
    res: TypeAnalysis = analyze_type(type_hint)

    assert res == expected


if __name__ == "__main__":
    pytest.main(["-q"])
