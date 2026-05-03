from __future__ import annotations

import typing
from typing import Annotated, Optional

import pytest
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


def optional_hint(tp: object) -> object:
    return Optional.__getitem__(tp)


@pytest.mark.parametrize(
    "type_hint, expected",
    [
        (optional_hint(int), TypeAnalysis(normalized_type=int | None, raw_type=int, is_optional=True, annotations=())),
        (int | None, TypeAnalysis(normalized_type=int | None, raw_type=int, is_optional=True, annotations=())),
        (optional_hint(str), TypeAnalysis(normalized_type=str | None, raw_type=str, is_optional=True, annotations=())),
        (str | None, TypeAnalysis(normalized_type=str | None, raw_type=str, is_optional=True, annotations=())),
    ],
)
def test_analyze_optional_types(type_hint: type, expected: TypeAnalysis) -> None:
    res: TypeAnalysis = analyze_type(type_hint)

    assert res == expected


@pytest.mark.parametrize(
    "type_hint, expected",
    [
        (
            int | str | None,
            TypeAnalysis(
                normalized_type=int | str | None,
                raw_type=int | str,
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
            Annotated[optional_hint(int), "a"],
            TypeAnalysis(normalized_type=int | None, raw_type=int, is_optional=True, annotations=("a",)),
        ),
        (
            Annotated[int | None, "a"],
            TypeAnalysis(normalized_type=int | None, raw_type=int, is_optional=True, annotations=("a",)),
        ),
        (
            optional_hint(Annotated[int, "b"]),
            TypeAnalysis(normalized_type=int | None, raw_type=int, is_optional=True, annotations=("b",)),
        ),
        (
            Annotated[int, "b"] | None,
            TypeAnalysis(normalized_type=int | None, raw_type=int, is_optional=True, annotations=("b",)),
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
