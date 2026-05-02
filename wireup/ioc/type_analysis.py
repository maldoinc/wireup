from dataclasses import dataclass
from functools import reduce
from operator import or_
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin


@dataclass(eq=True)
class TypeAnalysis:
    normalized_type: type
    """The type normalized to T | None (if optional) or T."""

    raw_type: type
    """The core inner type T, stripped of all Optional/Annotated wrappers."""

    is_optional: bool
    """True if None was found anywhere in the wrapping layers."""

    annotations: tuple[Any, ...]
    """All metadata collected from every Annotated layer found."""


def analyze_type(type_hint: Any) -> TypeAnalysis:
    current_type = type_hint
    annotations: list[Any] = []
    is_optional = False

    while True:
        origin = get_origin(current_type)
        args = get_args(current_type)

        if origin is Annotated:
            current_type = args[0]
            annotations.extend(args[1:])
            continue

        # Handle Union[T, None] / Optional[T] / T | None.
        if (origin is Union or origin is UnionType) and type(None) in args:
            is_optional = True
            union_without_none = tuple(arg for arg in args if arg is not type(None))

            current_type = (
                union_without_none[0]
                if len(union_without_none) == 1
                else reduce(or_, union_without_none[1:], union_without_none[0])
            )
            continue

        break

    return TypeAnalysis(
        normalized_type=current_type | None if is_optional else current_type,
        raw_type=current_type,  # type:ignore[arg-type, unused-ignore]
        is_optional=is_optional,
        annotations=tuple(annotations),
    )
