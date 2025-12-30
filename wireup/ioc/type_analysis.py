import sys
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple, Union

from typing_extensions import Annotated, get_args, get_origin

if sys.version_info >= (3, 10):
    from types import UnionType
else:
    UnionType = object()


@dataclass(eq=True)
class TypeAnalysis:
    normalized_type: type
    """The type normalized to Optional[T] (if optional) or T."""

    raw_type: type
    """The core inner type T, stripped of all Optional/Annotated wrappers."""

    is_optional: bool
    """True if None was found anywhere in the wrapping layers."""

    annotations: Tuple[Any, ...]
    """All metadata collected from every Annotated layer found."""


def analyze_type(type_hint: Any) -> TypeAnalysis:
    current_type = type_hint
    annotations: List[Any] = []
    is_optional = False

    while True:
        origin = get_origin(current_type)
        args = get_args(current_type)

        if origin is Annotated:
            current_type = args[0]
            annotations.extend(args[1:])
            continue

        # Handle Union[T, None] / Optional[T] / T | None (if on 3.10+)
        if (origin is Union or origin is UnionType) and type(None) in args:
            is_optional = True
            union_without_none = tuple(arg for arg in args if arg is not type(None))

            current_type = union_without_none[0] if len(union_without_none) == 1 else Union[union_without_none]  # type:ignore[reportUnknownVariableType, unused-ignore]
            continue

        break

    return TypeAnalysis(
        normalized_type=Optional[current_type] if is_optional else current_type,  # type:ignore[arg-type]
        raw_type=current_type,  # type:ignore[arg-type, unused-ignore]
        is_optional=is_optional,
        annotations=tuple(annotations),
    )
